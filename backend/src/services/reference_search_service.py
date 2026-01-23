"""参考文献搜索服务"""

import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from langchain_core.documents import Document

from .mcp_tools import MCPRouter
from .external_search_service import ExternalSearchService


class ReferenceItem(BaseModel):
    """参考文献项"""
    title: str = Field(description="标题")
    url: str = Field(description="链接")
    source: str = Field(description="来源")
    snippet: str = Field(description="摘要/片段")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ReferenceSearchResult(BaseModel):
    """参考文献搜索结果"""
    query: str = Field(description="搜索查询")
    total_results: int = Field(description="总结果数")
    references: List[ReferenceItem] = Field(description="参考文献列表")


class ReferenceSearchService:
    """参考文献搜索服务 - 整合本地和外部搜索"""
    
    def __init__(self):
        self.mcp_router = MCPRouter()
        self.external_search = ExternalSearchService()
    
    async def search_references_async(
        self,
        query: str,
        max_results: int = 10,
        preferred_sources: Optional[List[str]] = None,
        use_external: bool = True
    ) -> ReferenceSearchResult:
        """搜索参考文献（异步版本，整合本地和外部搜索）
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            preferred_sources: 优先知识源，如 ["arxiv", "wikipedia", "web"]
            use_external: 是否使用外部搜索（默认 True）
        
        Returns:
            ReferenceSearchResult: 搜索结果
        """
        references = []
        
        # 1. 外部搜索
        if use_external and self.external_search.is_available():
            try:
                # 使用 await 调用异步搜索
                external_result = await self.external_search.search_all(
                    query,
                    sources=preferred_sources,
                    max_results_per_source=max(2, max_results // 3)
                )
                
                # 转换外部搜索结果
                for result in external_result.results:
                    ref = ReferenceItem(
                        title=result.title,
                        url=result.url,
                        source=result.source,
                        snippet=result.snippet,
                        metadata={
                            "authors": result.authors,
                            "published": result.published,
                            "score": result.score
                        }
                    )
                    references.append(ref)
                
                print(f"✅ 外部搜索获得 {len(references)} 个结果")
            except Exception as e:
                print(f"⚠️ 外部搜索失败，回退到本地搜索: {e}")
        
        # 2. 使用 MCP 路由器补充
        if len(references) < max_results:
            try:
                remaining = max_results - len(references)
                docs = self.mcp_router.search(
                    query,
                    preferred_sources=preferred_sources or ["arxiv", "wikipedia"]
                )
                
                # 转换为参考文献项
                for doc in docs[:remaining]:
                    ref = ReferenceItem(
                        title=doc.metadata.get("title", query),
                        url=doc.metadata.get("url", ""),
                        source=doc.metadata.get("source", "local"),
                        snippet=self._truncate_text(doc.page_content, 300),
                        metadata=doc.metadata
                    )
                    references.append(ref)
                
                print(f"✅ 本地搜索补充 {len(docs[:remaining])} 个结果")
            except Exception as e:
                print(f"⚠️ 本地搜索失败: {e}")
        
        return ReferenceSearchResult(
            query=query,
            total_results=len(references),
            references=references
        )
    
    def search_references(
        self,
        query: str,
        max_results: int = 10,
        preferred_sources: Optional[List[str]] = None,
        use_external: bool = True
    ) -> ReferenceSearchResult:
        """搜索参考文献（同步版本，用于非异步上下文）
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            preferred_sources: 优先知识源，如 ["arxiv", "wikipedia", "web"]
            use_external: 是否使用外部搜索（默认 True）
        
        Returns:
            ReferenceSearchResult: 搜索结果
        """
        try:
            return asyncio.run(self.search_references_async(
                query, max_results, preferred_sources, use_external
            ))
        except RuntimeError as e:
            if "running" in str(e).lower():
                print(f"⚠️ 检测到运行中的事件循环，仅使用本地搜索")
                return self._search_local_only(query, max_results, preferred_sources)
            raise
    
    def _search_local_only(
        self,
        query: str,
        max_results: int,
        preferred_sources: Optional[List[str]] = None
    ) -> ReferenceSearchResult:
        """仅使用本地搜索（回退方法）"""
        references = []
        try:
            docs = self.mcp_router.search(
                query,
                preferred_sources=preferred_sources or ["arxiv", "wikipedia"]
            )
            
            for doc in docs[:max_results]:
                ref = ReferenceItem(
                    title=doc.metadata.get("title", query),
                    url=doc.metadata.get("url", ""),
                    source=doc.metadata.get("source", "local"),
                    snippet=self._truncate_text(doc.page_content, 300),
                    metadata=doc.metadata
                )
                references.append(ref)
        except Exception as e:
            print(f"⚠️ 本地搜索失败: {e}")
        
        return ReferenceSearchResult(
            query=query,
            total_results=len(references),
            references=references
        )
    
    async def search_by_concepts_async(
        self,
        concepts: List[str],
        max_results_per_concept: int = 3,
        use_external: bool = True
    ) -> Dict[str, ReferenceSearchResult]:
        """按概念列表搜索参考文献（异步版本）
        
        Args:
            concepts: 概念列表
            max_results_per_concept: 每个概念的最大结果数
            use_external: 是否使用外部搜索
        
        Returns:
            Dict[concept -> ReferenceSearchResult]: 按概念组织的搜索结果
        """
        results = {}

        if use_external and self.external_search.is_available():
            try:
                external_results = await self.external_search.search_by_concepts(
                    concepts,
                    max_results_per_concept=max_results_per_concept
                )
                
                # 转换结果格式
                for concept, external_result in external_results.items():
                    references = []
                    for result in external_result.results:
                        ref = ReferenceItem(
                            title=result.title,
                            url=result.url,
                            source=result.source,
                            snippet=result.snippet,
                            metadata={
                                "authors": result.authors,
                                "published": result.published
                            }
                        )
                        references.append(ref)
                    
                    results[concept] = ReferenceSearchResult(
                        query=concept,
                        total_results=len(references),
                        references=references
                    )
                
                return results
            except Exception as e:
                print(f"⚠️ 批量外部搜索失败，回退到逐个搜索: {e}")
        
        # 回退到逐个搜索
        for concept in concepts:
            try:
                result = await self.search_references_async(
                    concept,
                    max_results=max_results_per_concept,
                    use_external=use_external
                )
                results[concept] = result
            except Exception as e:
                print(f"搜索概念 '{concept}' 时出错: {e}")
                results[concept] = ReferenceSearchResult(
                    query=concept,
                    total_results=0,
                    references=[]
                )
        
        return results
    
    def search_by_concepts(
        self,
        concepts: List[str],
        max_results_per_concept: int = 3,
        use_external: bool = True
    ) -> Dict[str, ReferenceSearchResult]:
        """按概念列表搜索参考文献（同步版本）
        
        Args:
            concepts: 概念列表
            max_results_per_concept: 每个概念的最大结果数
            use_external: 是否使用外部搜索
        
        Returns:
            Dict[concept -> ReferenceSearchResult]: 按概念组织的搜索结果
        """
        try:
            return asyncio.run(self.search_by_concepts_async(
                concepts, max_results_per_concept, use_external
            ))
        except RuntimeError as e:
            if "running" in str(e).lower():
                print(f"⚠️ 检测到运行中的事件循环，回退到本地搜索")
                # 回退到本地搜索
                results = {}
                for concept in concepts:
                    results[concept] = self._search_local_only(
                        concept, max_results_per_concept
                    )
                return results
            raise
    
    def search_academic_papers(
        self,
        query: str,
        max_results: int = 5
    ) -> ReferenceSearchResult:
        """搜索学术论文（优先 Arxiv）"""
        return self.search_references(
            query,
            max_results=max_results,
            preferred_sources=["arxiv"]
        )
    
    def search_general_knowledge(
        self,
        query: str,
        max_results: int = 5
    ) -> ReferenceSearchResult:
        """搜索通用知识（优先 Wikipedia）"""
        return self.search_references(
            query,
            max_results=max_results,
            preferred_sources=["wikipedia", "baike"]
        )
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(" ", 1)[0] + "..."
