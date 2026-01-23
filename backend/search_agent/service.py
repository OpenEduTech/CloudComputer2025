from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import urllib.parse
import uuid
from dataclasses import dataclass
from typing import Any, List

import httpx


from common.models import Chunk, SourceInfo, ValidationInfo
from common.prompts import CLASSIFY_PROMPT, VALIDATE_PROMPT
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("search-agent-service")

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def hash_text(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

@dataclass
class SearchItem:
    url: str
    title: str
    content: str

class SearchService:
    def __init__(self) -> None:
        self.search_provider = os.getenv("SEARCH_PROVIDER", "tavily").strip().lower()
        self.tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
        self.openai_key = os.getenv("LLM_API_KEY", "").strip()
        self.openai_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip()
        self.openai_model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
        self.timeout_s = float(os.getenv("HTTP_TIMEOUT_S", "30"))
        self.llm_timeout_s = float(os.getenv("LLM_TIMEOUT_S", "120"))
        self.knowledge_engine_url = os.getenv("KNOWLEDGE_ENGINE_URL", "http://knowledge-engine:8002").strip()
        self.wiki_lang = os.getenv("WIKIPEDIA_LANG", "zh").strip().lower()
        

    async def classify(self, concept: str, max_disciplines: int = 5, min_relevance: float = 0.3) -> dict[str, Any]:
        """调用 LLM 对概念进行学科分类"""
        if self.openai_key:
            try:
                payload = await self._llm_json(CLASSIFY_PROMPT.format(concept=concept))
                disciplines = payload.get("disciplines") or []
                disciplines = [d for d in disciplines if float(d.get("relevance_score", 0)) >= min_relevance]
                disciplines = disciplines[:max_disciplines]
                for i, d in enumerate(disciplines, start=1):
                    d.setdefault("id", f"d{i}")
                    d.setdefault("is_primary", i == 1)
                payload["disciplines"] = disciplines
                payload["primary_discipline"] = payload.get("primary_discipline") or (disciplines[0]["name"] if disciplines else "综合")
                payload.setdefault("suggested_additions", [])
                return payload
            except Exception as e:
                logger.exception("LLM classify failed, fallback enabled. concept=%s err=%s", concept, e)

        # Fallback 逻辑
        default = [
            ("数学", ["概率论 熵", "KL散度", "最大熵 原理"]),
            ("物理学-热力学", [f"{concept} 热力学 第二定律", "克劳修斯 熵", "熵增原理"]),
            ("信息论", [f"{concept} 香农", "信息熵 定义", "编码 定理"]),
            ("统计力学", [f"{concept} 玻尔兹曼", "微观态 宏观态", "配分函数"]),
            ("机器学习", [f"{concept} 交叉熵 损失", "信息增益 决策树", "最大熵模型"]),
        ][:max_disciplines]

        ds = []
        for i, (name, kws) in enumerate(default, start=1):
            score = max(0.4, 1.0 - (i - 1) * 0.12)
            if score < min_relevance:
                continue
            ds.append(
                {
                    "id": f"d{i}",
                    "name": name,
                    "relevance_score": score,
                    "reason": f"规则模板生成（fallback），用于启动跨学科检索：{name}",
                    "search_keywords": kws,
                    "is_primary": i == 1,
                }
            )
        return {
            "concept": concept,
            "primary_discipline": ds[0]["name"] if ds else "综合",
            "disciplines": ds,
            "suggested_additions": [],
        }

    async def search(self, query: str, max_results: int) -> List[SearchItem]:
        """统一搜索入口"""
        if self.search_provider == "tavily":
            return await self._tavily_search(query, max_results)
        if self.search_provider == "mock":
            return await self._mock_search(query, max_results)
        # default wikipedia
        return await self._wikipedia_search(query, max_results)

    async def validate_results(self, concept: str, items: List[SearchItem]) -> dict[str, Any]:
        """批量验证检索结果的相关性"""
        if not self.openai_key or not items:
            return {}
        
        # 限制验证数量以防 Token 溢出，取前 30 个
        cand = [{"url": it.url, "title": it.title, "content": it.content[:800]} for it in items[:30]]
        
        try:
            resp = await self._llm_json(
                VALIDATE_PROMPT.format(concept=concept, items_json=json.dumps(cand, ensure_ascii=False))
            )
            validated_meta = {}
            for v in resp.get("validated", []) or []:
                validated_meta[v.get("url", "")] = v
            return validated_meta
        except Exception as e:
            print(f"LLM Validation Failed: {e}")
            # 验证失败降级为全部通过（由上层逻辑处理默认值）
            return {}

    async def ingest_chunks(self, concept: str, chunks: List[Chunk]) -> None:
        """发送 Chunk 到 Knowledge Engine"""
        url = f"{self.knowledge_engine_url.rstrip('/')}/api/ingest"
        payload = {"concept": concept, "chunks": [c.model_dump() for c in chunks]}
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            try:
                await client.post(url, json=payload)
            except Exception:
                # ingest失败不影响search结果返回（容错）
                return

    # --- Internal Provider Methods ---

    async def _tavily_search(self, query: str, max_results: int) -> List[SearchItem]:
        if not self.tavily_key:
            return []

        url = "https://api.tavily.com/search"
        body = {
            "api_key": self.tavily_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(url, json=body)
            r.raise_for_status()
            data = r.json()

        items: List[SearchItem] = []
        for it in data.get("results", []) or []:
            items.append(
                SearchItem(
                    url=it.get("url", "") or "",
                    title=it.get("title", "") or "",
                    content=clean_text(it.get("content", "") or it.get("snippet", "") or ""),
                )
            )
        return items

    async def _wikipedia_search(self, query: str, max_results: int) -> List[SearchItem]:
        lang = "zh" if self.wiki_lang not in ("zh", "en") else self.wiki_lang
        opensearch = f"https://{lang}.wikipedia.org/w/api.php"

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            # 1. OpenSearch to get titles
            r = await client.get(
                opensearch,
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": str(max(1, min(max_results, 10))),
                    "namespace": "0",
                    "format": "json",
                },
                headers={"User-Agent": "CloudComputer2025-SearchAgent/0.1"},
            )
            r.raise_for_status()
            data = r.json()

            titles = data[1] if isinstance(data, list) and len(data) > 1 else []
            urls = data[3] if isinstance(data, list) and len(data) > 3 else []

            items: List[SearchItem] = []
            for title, page_url in list(zip(titles, urls))[:max_results]:
                # 2. Summary REST to get content
                safe_title = urllib.parse.quote(title, safe="")
                summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
                try:
                    sr = await client.get(summary_url, headers={"User-Agent": "CloudComputer2025-SearchAgent/0.1"})
                    if sr.status_code != 200:
                        continue
                    sdata = sr.json()
                    extract = clean_text(sdata.get("extract", "") or "")
                    if len(extract) < 80:
                        continue
                    items.append(SearchItem(url=page_url, title=title, content=extract))
                except Exception:
                    continue
        return items

    async def _mock_search(self, query: str, max_results: int) -> List[SearchItem]:
        base = (
            f"Mock result for query='{query}'. "
            "This is offline demo text. It should be replaced by real provider in production."
        )
        return [
            SearchItem(
                url="about:mock",
                title="mock-search",
                content=base + " " + ("More details. " * 20),
            )
        ][:max_results]

    async def _llm_json(self, prompt: str) -> dict[str, Any]:
        url = f"{self.openai_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}"}
        body = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.llm_timeout_s) as client:
                    r = await client.post(url, headers=headers, json=body)
                    r.raise_for_status()
                    data = r.json()
                content = data["choices"][0]["message"]["content"]
                # 简单清洗 markdown 标记
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                return json.loads(content.strip())
            except httpx.HTTPStatusError as e:
                last_exc = e
                if e.response.status_code == 429:
                    await asyncio.sleep(5.0 * (attempt + 1))
                else:
                    await asyncio.sleep(1.0 * (attempt + 1))
            except Exception as e:
                last_exc = e
                await asyncio.sleep(1.0 * (attempt + 1))

        raise last_exc