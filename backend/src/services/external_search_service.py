"""外部资源搜索服务 - 联网搜索 Wikipedia、Arxiv、Web"""

import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """搜索结果项"""
    title: str = Field(description="标题")
    url: str = Field(description="链接")
    source: str = Field(description="来源（wikipedia/arxiv/web）")
    snippet: str = Field(description="摘要/片段")
    authors: Optional[List[str]] = Field(default=None, description="作者（仅学术论文）")
    published: Optional[str] = Field(default=None, description="发布日期")
    score: Optional[float] = Field(default=None, description="相关性评分")


class ExternalSearchResult(BaseModel):
    """外部搜索结果"""
    query: str = Field(description="搜索查询")
    total_results: int = Field(description="总结果数")
    results: List[SearchResult] = Field(description="搜索结果列表")
    sources_used: List[str] = Field(description="使用的搜索源")


class ExternalSearchService:
    """外部资源搜索服务"""
    
    def __init__(self):
        """初始化"""
        self._wikipedia_available = False
        self._arxiv_available = False
        self._web_available = False
        
        # 导入各个搜索库
        try:
            import wikipedia
            self._wikipedia = wikipedia
            self._wikipedia_available = True
            logger.info("✅ Wikipedia 搜索已启用")
        except ImportError:
            logger.warning("⚠️ Wikipedia 库未安装，Wikipedia 搜索不可用")
        
        try:
            import arxiv
            self._arxiv = arxiv
            self._arxiv_available = True
            logger.info("✅ Arxiv 搜索已启用")
        except ImportError:
            logger.warning("⚠️ Arxiv 库未安装，Arxiv 搜索不可用")
        
        try:
            from duckduckgo_search import DDGS
            self._ddgs = DDGS
            self._web_available = True
            logger.info("✅ Web 搜索已启用（DuckDuckGo）")
        except ImportError:
            logger.warning("⚠️ DuckDuckGo 搜索库未安装，Web 搜索不可用")
    
    async def search_wikipedia(
        self,
        query: str,
        max_results: int = 3,
        lang: str = "zh"
    ) -> List[SearchResult]:
        """搜索 Wikipedia
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            lang: 语言（zh/en）
        
        Returns:
            搜索结果列表
        """
        if not self._wikipedia_available:
            logger.warning("Wikipedia 搜索不可用")
            return []
        
        try:
            self._wikipedia.set_lang(lang)
  
            search_results = self._wikipedia.search(query, results=max_results)
            
            results = []
            for title in search_results[:max_results]:
                try:
                    page = self._wikipedia.page(title, auto_suggest=False)
                    
                    result = SearchResult(
                        title=page.title,
                        url=page.url,
                        source="wikipedia",
                        snippet=page.summary[:300] + "..." if len(page.summary) > 300 else page.summary,
                        published=None,
                        authors=None
                    )
                    results.append(result)
                except Exception as e:
                    logger.warning(f"获取 Wikipedia 页面失败 '{title}': {e}")
                    continue
            
            logger.info(f"✅ Wikipedia 搜索完成: {query} -> {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"❌ Wikipedia 搜索失败: {e}")
            return []
    
    async def search_arxiv(
        self,
        query: str,
        max_results: int = 3
    ) -> List[SearchResult]:
        """搜索 Arxiv 学术论文
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
        
        Returns:
            搜索结果列表
        """
        if not self._arxiv_available:
            logger.warning("Arxiv 搜索不可用")
            return []
        
        try:
            # 创建搜索客户端
            client = self._arxiv.Client()

            search = self._arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=self._arxiv.SortCriterion.Relevance
            )
            
            results = []
            for paper in client.results(search):
                authors = [author.name for author in paper.authors[:3]]  
                if len(paper.authors) > 3:
                    authors.append("et al.")
                
                result = SearchResult(
                    title=paper.title,
                    url=paper.entry_id,
                    source="arxiv",
                    snippet=paper.summary[:300] + "..." if len(paper.summary) > 300 else paper.summary,
                    authors=authors,
                    published=paper.published.strftime("%Y-%m-%d") if paper.published else None
                )
                results.append(result)
            
            logger.info(f"✅ Arxiv 搜索完成: {query} -> {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"❌ Arxiv 搜索失败: {e}")
            return []
    
    async def search_web(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """搜索 Web（使用 DuckDuckGo）
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
        
        Returns:
            搜索结果列表
        """
        if not self._web_available:
            logger.warning("Web 搜索不可用")
            return []
        
        try:
            # 创建搜索实例
            ddgs = self._ddgs()
            
            search_results = ddgs.text(query, max_results=max_results)
            
            results = []
            for item in search_results:
                result = SearchResult(
                    title=item.get("title", "无标题"),
                    url=item.get("href", ""),
                    source="web",
                    snippet=item.get("body", "")[:300],
                    published=None,
                    authors=None
                )
                results.append(result)
            
            logger.info(f"✅ Web 搜索完成: {query} -> {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"❌ Web 搜索失败: {e}")
            return []
    
    async def search_all(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        max_results_per_source: int = 3
    ) -> ExternalSearchResult:
        """综合搜索所有来源
        
        Args:
            query: 搜索查询
            sources: 指定搜索源列表，如 ["wikipedia", "arxiv", "web"]，None 表示全部
            max_results_per_source: 每个来源的最大结果数
        
        Returns:
            综合搜索结果
        """
        # 默认搜索所有可用源
        if sources is None:
            sources = []
            if self._wikipedia_available:
                sources.append("wikipedia")
            if self._arxiv_available:
                sources.append("arxiv")
            if self._web_available:
                sources.append("web")
        
        logger.info(f"🔍 开始综合搜索: {query}, 来源: {sources}")
        
        # 并发搜索所有来源
        tasks = []
        sources_used = []
        
        if "wikipedia" in sources and self._wikipedia_available:
            tasks.append(self.search_wikipedia(query, max_results_per_source))
            sources_used.append("wikipedia")
        
        if "arxiv" in sources and self._arxiv_available:
            tasks.append(self.search_arxiv(query, max_results_per_source))
            sources_used.append("arxiv")
        
        if "web" in sources and self._web_available:
            tasks.append(self.search_web(query, max_results_per_source))
            sources_used.append("web")
        
        all_results = []
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in search_results:
                if isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"搜索任务失败: {result}")
        
        logger.info(f"✅ 综合搜索完成: {query} -> {len(all_results)} 个结果")
        
        return ExternalSearchResult(
            query=query,
            total_results=len(all_results),
            results=all_results,
            sources_used=sources_used
        )
    
    async def search_by_concepts(
        self,
        concepts: List[str],
        sources: Optional[List[str]] = None,
        max_results_per_concept: int = 2
    ) -> Dict[str, ExternalSearchResult]:
        """按概念列表搜索
        
        Args:
            concepts: 概念列表
            sources: 指定搜索源
            max_results_per_concept: 每个概念的最大结果数
        
        Returns:
            按概念组织的搜索结果
        """
        logger.info(f"🔍 开始按概念搜索: {len(concepts)} 个概念")
        
        # 并发搜索所有概念
        tasks = [
            self.search_all(concept, sources, max_results_per_concept)
            for concept in concepts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 组织结果
        concept_results = {}
        for concept, result in zip(concepts, results):
            if isinstance(result, ExternalSearchResult):
                concept_results[concept] = result
            else:
                logger.error(f"概念 '{concept}' 搜索失败: {result}")
                concept_results[concept] = ExternalSearchResult(
                    query=concept,
                    total_results=0,
                    results=[],
                    sources_used=[]
                )
        
        logger.info(f"✅ 按概念搜索完成: {len(concept_results)} 个概念")
        return concept_results
    
    def get_available_sources(self) -> List[str]:
        """获取可用的搜索源列表
        
        Returns:
            可用搜索源列表
        """
        sources = []
        if self._wikipedia_available:
            sources.append("wikipedia")
        if self._arxiv_available:
            sources.append("arxiv")
        if self._web_available:
            sources.append("web")
        return sources
    
    def is_available(self) -> bool:
        """检查是否有任何搜索源可用
        
        Returns:
            是否有可用的搜索源
        """
        return self._wikipedia_available or self._arxiv_available or self._web_available

