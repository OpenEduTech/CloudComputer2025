"""
知识扩充Agent
"""
from openai import AsyncOpenAI
import httpx
import logging
from typing import List, Dict, Any
import json
import feedparser

from app.core.config import settings
from app.core.llm_validation import validate_knowledge_response
from app.models.schemas import KnowledgeExpansion, ExternalResource

logger = logging.getLogger(__name__)


class KnowledgeExpansionAgent:
    """知识扩充Agent"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.deepseek_api_base
        )
        self.model = settings.DEEPSEEK_MODEL
        self.temperature = settings.TEMPERATURE
    
    async def expand_knowledge(
        self,
        query: str,
        context: str = "",
        max_length: int = 500,
        include_external: bool = True
    ) -> KnowledgeExpansion:
        """
        扩充知识点
        
        Args:
            query: 要扩充的知识点
            context: 上下文信息（如PPT内容）
            max_length: 扩充内容最大长度
            include_external: 是否包含外部资源
        """
        try:
            # 使用CoT（Chain of Thought）提示词
            prefilter_hint = ""
            if settings.LOCAL_PREFILTER_ENABLED and context:
                prefilter_hint = self._local_prefilter(context)

            prompt = self._build_expansion_prompt(query, context, max_length, prefilter_hint)
            
            # 调用LLM
            response = await self._call_llm(prompt)
            
            # 解析响应
            expansion_data = self._parse_llm_response(response)

            llm_validation = None
            if settings.LLM_VALIDATION_ENABLED:
                llm_validation = validate_knowledge_response(response, expansion_data)
            
            # 获取外部资源
            external_resources = []
            if include_external:
                external_resources = await self._fetch_external_resources(query)
            
            return KnowledgeExpansion(
                query=query,
                expansion=expansion_data.get("explanation", ""),
                formulas=expansion_data.get("formulas", []),
                code_examples=expansion_data.get("code_examples", []),
                external_resources=external_resources,
                related_topics=expansion_data.get("related_topics", []),
                llm_validation=llm_validation
            )
            
        except Exception as e:
            logger.error(f"知识扩充失败: {e}", exc_info=True)
            raise
    
    def _build_expansion_prompt(self, query: str, context: str, max_length: int, prefilter_hint: str) -> str:
        """构建扩充提示词（CoT模式）"""
        prefilter_section = f"\n本地预筛要点（可选参考）：\n{prefilter_hint}\n" if prefilter_hint else ""
        prompt = f"""你是一个专业的教学助手，擅长扩充和解释知识点。

任务：针对给定的知识点，提供详细、准确的扩充说明。

知识点：{query}

上下文信息：
{context if context else "无"}
{prefilter_section}

要求：
1. 提供清晰的原理说明、元知识解释和背景知识
2. 如果涉及公式，给出完整的公式推导
3. 如果适用，提供代码示例（Python优先）
4. 列出3-5个相关主题供延伸学习
5. 内容控制在{max_length}字以内
6. 确保内容准确性，避免幻觉

请按以下JSON格式返回（仅输出JSON，不要输出额外文字）：
{{
    "explanation": "详细解释",
    "formulas": ["公式1", "公式2"],
    "code_examples": [
        {{
            "language": "python",
            "code": "代码示例",
            "description": "代码说明"
        }}
    ],
    "related_topics": ["相关主题1", "相关主题2"]
}}

思考步骤：
1. 分析知识点的核心概念
2. 确定需要的背景知识
3. 构建逻辑清晰的解释
4. 验证内容的准确性
5. 组织输出格式

请开始："""
        return prompt

    def _local_prefilter(self, context: str) -> str:
        """本地预筛（占位）：用于大批量请求的初筛摘要"""
        # 说明：此处为轻量化占位实现，实际可替换为本地量化模型输出
        lines = [line.strip() for line in context.split("\n") if line.strip()]
        return " | ".join(lines[:6])
    
    async def _call_llm(self, prompt: str, retries: int = 0) -> str:
        """
        调用LLM（带重试和校验）
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的教学助手，提供准确、详细的知识解释。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            # 校验层：检查响应是否为空
            if not content or len(content.strip()) < 10:
                raise ValueError("LLM返回内容过短或为空")
            
            return content
            
        except Exception as e:
            if retries < settings.MAX_RETRIES:
                logger.warning(f"LLM调用失败，重试 {retries + 1}/{settings.MAX_RETRIES}: {e}")
                return await self._call_llm(prompt, retries + 1)
            else:
                logger.error(f"LLM调用失败，已达最大重试次数: {e}")
                raise
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        解析LLM响应（带校验）
        """
        try:
            # 尝试提取JSON
            # 有时LLM会在JSON前后添加文字说明，需要提取
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                
                # 校验必需字段
                if "explanation" not in data:
                    logger.warning("LLM响应缺少explanation字段")
                    data["explanation"] = response  # 降级策略：使用原始响应
                
                return data
            else:
                # 降级策略：解析失败时返回基本结构
                logger.warning("无法从LLM响应中提取JSON，使用降级策略")
                return {
                    "explanation": response,
                    "formulas": [],
                    "code_examples": [],
                    "related_topics": []
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            # 降级策略
            return {
                "explanation": response,
                "formulas": [],
                "code_examples": [],
                "related_topics": []
            }
    
    async def _fetch_external_resources(self, query: str) -> List[ExternalResource]:
        """获取外部资源（多维搜索）"""
        resources: List[ExternalResource] = []
        
        # Wikipedia搜索
        if settings.WIKIPEDIA_API_ENABLED:
            wiki_resources = await self._search_wikipedia(query)
            resources.extend(wiki_resources)
        
        # Arxiv搜索（学术）
        if settings.ARXIV_API_ENABLED:
            arxiv_resources = await self._search_arxiv(query)
            resources.extend(arxiv_resources)

        # Semantic Scholar
        if settings.SEMANTIC_SCHOLAR_API_ENABLED:
            ss_resources = await self._search_semantic_scholar(query)
            resources.extend(ss_resources)

        # OpenAlex
        if settings.OPENALEX_API_ENABLED:
            oa_resources = await self._search_openalex(query)
            resources.extend(oa_resources)

        # StackExchange
        if settings.STACKEXCHANGE_API_ENABLED:
            se_resources = await self._search_stackexchange(query)
            resources.extend(se_resources)

        # Bing Search
        if settings.BING_SEARCH_API_ENABLED:
            bing_resources = await self._search_bing(query)
            resources.extend(bing_resources)

        # Google CSE
        if settings.GOOGLE_CSE_API_ENABLED:
            google_resources = await self._search_google_cse(query)
            resources.extend(google_resources)
        
        # 去重与截断
        deduped = []
        seen = set()
        for r in resources:
            key = r.url or r.title
            if key in seen:
                continue
            seen.add(key)
            deduped.append(r)

        return deduped[:8]  # 最多返回8个外部资源
    
    async def _search_wikipedia(self, query: str) -> List[ExternalResource]:
        """搜索Wikipedia"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Wikipedia API搜索
                search_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": 3
                }
                
                response = await client.get(search_url, params=params)
                data = response.json()
                
                resources = []
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "")
                    page_id = item.get("pageid", "")
                    snippet = item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
                    
                    resources.append(ExternalResource(
                        source="Wikipedia",
                        title=title,
                        url=f"https://en.wikipedia.org/?curid={page_id}",
                        summary=snippet
                    ))
                
                return resources
                
        except Exception as e:
            logger.error(f"Wikipedia搜索失败: {e}")
            return []
    
    async def _search_arxiv(self, query: str) -> List[ExternalResource]:
        """搜索Arxiv学术论文"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_url = "http://export.arxiv.org/api/query"
                params = {
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": 3
                }
                
                response = await client.get(search_url, params=params)
                feed = feedparser.parse(response.text)

                resources = []
                for entry in feed.entries[:3]:
                    resources.append(ExternalResource(
                        source="Arxiv",
                        title=entry.get("title", ""),
                        url=entry.get("link", ""),
                        summary=entry.get("summary", "").replace("\n", " ")
                    ))

                return resources
                
        except Exception as e:
            logger.error(f"Arxiv搜索失败: {e}")
            return []

    async def _search_semantic_scholar(self, query: str) -> List[ExternalResource]:
        """搜索Semantic Scholar"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
                headers = {}
                if settings.SEMANTIC_SCHOLAR_API_KEY:
                    headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY

                params = {
                    "query": query,
                    "limit": 3,
                    "fields": "title,abstract,url,year,authors"
                }
                response = await client.get(search_url, params=params, headers=headers)
                data = response.json()

                resources = []
                for item in data.get("data", [])[:3]:
                    title = item.get("title", "")
                    abstract = item.get("abstract", "") or ""
                    url = item.get("url", "")
                    resources.append(ExternalResource(
                        source="Semantic Scholar",
                        title=title,
                        url=url,
                        summary=abstract[:500]
                    ))

                return resources
        except Exception as e:
            logger.error(f"Semantic Scholar搜索失败: {e}")
            return []

    async def _search_openalex(self, query: str) -> List[ExternalResource]:
        """搜索OpenAlex知识图谱"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_url = "https://api.openalex.org/works"
                params = {
                    "search": query,
                    "per-page": 3
                }
                if settings.OPENALEX_EMAIL:
                    params["mailto"] = settings.OPENALEX_EMAIL

                response = await client.get(search_url, params=params)
                data = response.json()

                resources = []
                for item in data.get("results", [])[:3]:
                    title = item.get("title", "")
                    url = item.get("id", "")
                    summary = item.get("abstract_inverted_index", {})
                    summary_text = ""
                    if isinstance(summary, dict):
                        summary_text = " ".join(summary.keys())[:500]

                    resources.append(ExternalResource(
                        source="OpenAlex",
                        title=title,
                        url=url,
                        summary=summary_text
                    ))

                return resources
        except Exception as e:
            logger.error(f"OpenAlex搜索失败: {e}")
            return []

    async def _search_stackexchange(self, query: str) -> List[ExternalResource]:
        """搜索StackExchange问答"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_url = "https://api.stackexchange.com/2.3/search/advanced"
                params = {
                    "order": "desc",
                    "sort": "relevance",
                    "q": query,
                    "site": "stackoverflow",
                    "pagesize": 3
                }
                if settings.STACKEXCHANGE_KEY:
                    params["key"] = settings.STACKEXCHANGE_KEY

                response = await client.get(search_url, params=params)
                data = response.json()

                resources = []
                for item in data.get("items", [])[:3]:
                    title = item.get("title", "")
                    url = item.get("link", "")
                    summary = f"Score: {item.get('score', 0)}"
                    resources.append(ExternalResource(
                        source="StackExchange",
                        title=title,
                        url=url,
                        summary=summary
                    ))

                return resources
        except Exception as e:
            logger.error(f"StackExchange搜索失败: {e}")
            return []

    async def _search_bing(self, query: str) -> List[ExternalResource]:
        """搜索Bing（需API Key）"""
        if not settings.BING_SEARCH_API_KEY:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_url = "https://api.bing.microsoft.com/v7.0/search"
                headers = {"Ocp-Apim-Subscription-Key": settings.BING_SEARCH_API_KEY}
                params = {"q": query, "count": 3}
                response = await client.get(search_url, headers=headers, params=params)
                data = response.json()

                resources = []
                for item in data.get("webPages", {}).get("value", [])[:3]:
                    resources.append(ExternalResource(
                        source="Bing Search",
                        title=item.get("name", ""),
                        url=item.get("url", ""),
                        summary=item.get("snippet", "")
                    ))

                return resources
        except Exception as e:
            logger.error(f"Bing搜索失败: {e}")
            return []

    async def _search_google_cse(self, query: str) -> List[ExternalResource]:
        """搜索Google CSE（需API Key和Engine ID）"""
        if not settings.GOOGLE_CSE_API_KEY or not settings.GOOGLE_CSE_ENGINE_ID:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "q": query,
                    "key": settings.GOOGLE_CSE_API_KEY,
                    "cx": settings.GOOGLE_CSE_ENGINE_ID,
                    "num": 3
                }
                response = await client.get(search_url, params=params)
                data = response.json()

                resources = []
                for item in data.get("items", [])[:3]:
                    resources.append(ExternalResource(
                        source="Google CSE",
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        summary=item.get("snippet", "")
                    ))

                return resources
        except Exception as e:
            logger.error(f"Google CSE搜索失败: {e}")
            return []
