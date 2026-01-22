"""
跨学科知识图谱智能体（增强版）
特点：
- 直接生成结构化 JSON 图谱（多学科、多跳、桥梁边）
- 可选：使用 Tavily 搜索证据做保守修正（无 key 也可运行）
- 具备容错：JSON 提取/修复、重试、置信度控制
"""
from __future__ import annotations
import os
import json
import time
import traceback
from typing import Dict, Any, List, Tuple

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

try:
    from tavily import TavilyClient
except Exception:
    TavilyClient = None  # 允许无 tavily 依赖时运行（但 requirements 已包含）

from prompt_templates import get_mining_graph_prompt, get_refine_prompt
from parser import normalize_graph

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.2))

# 规模控制（可用 .env 覆盖）
MAX_EVIDENCE_QUERIES = int(os.getenv("MAX_EVIDENCE_QUERIES", "8"))
EVIDENCE_PER_QUERY = int(os.getenv("EVIDENCE_PER_QUERY", "2"))
SLEEP_BETWEEN_QUERIES = float(os.getenv("SLEEP_BETWEEN_QUERIES", "0.2"))

def _extract_json(text: str) -> str:
    # 与 parser 中相同逻辑，避免循环引用
    import re
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if m:
        return m.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    raise ValueError("No JSON object found in LLM output.")

class EnhancedCrossDisciplineAgent:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 未设置（请在 .env 中配置）")

        self.llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE
        )

        self.tavily = None
        if TAVILY_API_KEY and TavilyClient is not None:
            try:
                self.tavily = TavilyClient(api_key=TAVILY_API_KEY)
            except Exception:
                self.tavily = None

    def _llm_invoke_json(self, prompt: str, retries: int = 2) -> Dict[str, Any]:
        last_err = None
        for _ in range(retries + 1):
            try:
                out = self.llm.invoke(prompt).content
                js = _extract_json(out)
                return json.loads(js)
            except Exception as e:
                last_err = e
                time.sleep(0.5)
        raise RuntimeError(f"LLM 输出 JSON 解析失败：{last_err}")

    def _collect_evidence(self, graph: Dict[str, Any]) -> str:
        """针对部分边收集证据，输出文本供二次修正。无 Tavily 时返回空证据。"""
        if not self.tavily:
            return ""

        # 选择“跨学科桥梁边”优先：两端 discipline 不同
        id_to_node = {n["id"]: n for n in graph["nodes"]}
        scored_edges = []
        for e in graph["edges"]:
            s = id_to_node.get(e["source"])
            t = id_to_node.get(e["target"])
            if not s or not t:
                continue
            cross = 1 if s.get("discipline") != t.get("discipline") else 0
            score = cross * 2 + float(e.get("confidence", 0.6))
            scored_edges.append((score, e, s, t))

        scored_edges.sort(key=lambda x: x[0], reverse=True)
        selected = scored_edges[:MAX_EVIDENCE_QUERIES]

        chunks = []
        for i, (_, e, s, t) in enumerate(selected, 1):
            query = f"{s['name']} 与 {t['name']} 关系"
            try:
                resp = self.tavily.search(query=query, max_results=EVIDENCE_PER_QUERY, search_depth="basic")
                snippets = []
                for r in resp.get("results", [])[:EVIDENCE_PER_QUERY]:
                    title = r.get("title","")
                    content = (r.get("content","") or "")[:220]
                    snippets.append(f"- {title}: {content}")
                snippet_text = "\n".join(snippets) if snippets else "- （无结果）"
            except Exception as ex:
                snippet_text = f"- （查询失败：{ex}）"

            chunks.append(f"[Evidence {i}]\nquery: {query}\n{snippet_text}\n")
            time.sleep(SLEEP_BETWEEN_QUERIES)

        return "\n".join(chunks)

    def generate_graph(self, concept: str) -> Dict[str, Any]:
        """主入口：生成增强图谱，并尽量做证据修正"""
        concept = (concept or "").strip()
        if not concept:
            raise ValueError("concept is required")

        # Phase 1: 直接生成 JSON 图谱
        raw1 = self._llm_invoke_json(get_mining_graph_prompt(concept))
        g1 = normalize_graph(raw1, concept)

        # Phase 2: 可选证据修正（保守）
        evidence = self._collect_evidence(g1)
        if evidence:
            try:
                refined_raw = self._llm_invoke_json(get_refine_prompt(json.dumps(g1, ensure_ascii=False), evidence))
                g2 = normalize_graph(refined_raw, concept)
                return g2
            except Exception:
                # 证据修正失败就退回 g1
                return g1

        return g1

# 单例
_agent = None
def get_agent() -> EnhancedCrossDisciplineAgent:
    global _agent
    if _agent is None:
        _agent = EnhancedCrossDisciplineAgent()
    return _agent
