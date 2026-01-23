"""
数据抓取模块
从Wikipedia和Arxiv抓取概念定义和学术证据
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
import aiohttp
import re
from urllib.parse import quote
import wikipedia

logger = logging.getLogger(__name__)


class DataCrawler:
    """数据抓取器（Wikipedia + Arxiv）"""
    
    def __init__(
        self,
        wikipedia_api_url: Optional[str] = None,
        arxiv_api_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 2
    ):
        """
        初始化数据抓取器
        
        Args:
            wikipedia_api_url: Wikipedia API URL
            arxiv_api_url: Arxiv API URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.wikipedia_api_url = wikipedia_api_url or os.getenv(
            "WIKIPEDIA_API_URL",
            "https://zh.wikipedia.org/api/rest_v1"
        )
        self.arxiv_api_url = arxiv_api_url or os.getenv(
            "ARXIV_API_URL",
            "http://export.arxiv.org/api/query"
        )
        self.timeout = timeout
        self.max_retries = max_retries
        
        logger.info("DataCrawler initialized")
    
    async def _fetch_with_retry(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Optional[str]:
        """
        带重试的HTTP请求
        
        Args:
            url: 请求URL
            params: 查询参数
            headers: 请求头
            
        Returns:
            响应文本，失败返回None
        """
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logger.warning(f"HTTP {response.status} for {url}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
            except Exception as e:
                logger.warning(f"Request failed: {e} (attempt {attempt + 1})")
            
            if attempt < self.max_retries:
                await asyncio.sleep(1)  # 重试前等待1秒
        
        return None
    
    async def search_wikipedia(
        self,
        concept: str,
        language: str = "zh"
    ) -> Optional[Dict[str, Any]]:
        """
        在Wikipedia中搜索概念（使用wikipedia官方库）
        
        Args:
            concept: 概念名称
            language: 语言代码（zh/en）
            
        Returns:
            {
                "title": 标题,
                "summary": 摘要,
                "url": 完整URL,
                "exists": 是否存在
            }
        """
        try:
            # 设置语言
            wikipedia.set_lang(language)
            
            # 异步包装同步调用
            loop = asyncio.get_event_loop()
            
            # 获取页面
            try:
                page = await loop.run_in_executor(None, wikipedia.page, concept)
                
                return {
                    "title": page.title,
                    "summary": page.summary[:500] if page.summary else "",
                    "url": page.url,
                    "exists": True
                }
                
            except wikipedia.exceptions.DisambiguationError as e:
                # 歧义页面，选择第一个选项
                logger.info(f"Wikipedia disambiguation for '{concept}': {e.options[:3]}")
                if e.options:
                    page = await loop.run_in_executor(None, wikipedia.page, e.options[0])
                    return {
                        "title": page.title,
                        "summary": page.summary[:500] if page.summary else "",
                        "url": page.url,
                        "exists": True
                    }
                else:
                    raise
                    
            except wikipedia.exceptions.PageError:
                logger.info(f"Wikipedia page not found: {concept}")
                return {
                    "title": concept,
                    "summary": "",
                    "url": "",
                    "exists": False
                }
            
        except Exception as e:
            logger.error(f"Failed to search Wikipedia: {e}")
            return {
                "title": concept,
                "summary": "",
                "url": "",
                "exists": False
            }
    
    async def get_wikipedia_definition(
        self,
        concept: str,
        max_length: int = 500
    ) -> str:
        """
        获取概念的Wikipedia定义
        
        Args:
            concept: 概念名称
            max_length: 最大返回长度
            
        Returns:
            定义文本
        """
        result = await self.search_wikipedia(concept)
        
        if not result["exists"] or not result["summary"]:
            # 尝试英文Wikipedia
            result_en = await self.search_wikipedia(concept, language="en")
            if result_en["exists"]:
                summary = result_en["summary"]
            else:
                return ""
        else:
            summary = result["summary"]
        
        # 截断到第一段或最大长度
        first_para = summary.split('\n')[0]
        if len(first_para) > max_length:
            first_para = first_para[:max_length] + "..."
        
        return first_para
    
    async def verify_concept_exists(
        self,
        concept: str
    ) -> Dict[str, Any]:
        """
        验证概念是否在Wikipedia中存在（用于可信度验证）
        
        Args:
            concept: 概念名称
            
        Returns:
            {
                "exists": bool,
                "source": "zh-wiki"/"en-wiki"/None,
                "url": str,
                "summary": str
            }
        """
        # 先尝试中文
        result_zh = await self.search_wikipedia(concept, language="zh")
        if result_zh["exists"]:
            return {
                "exists": True,
                "source": "zh-wiki",
                "url": result_zh["url"],
                "summary": result_zh["summary"][:200]
            }
        
        # 再尝试英文
        result_en = await self.search_wikipedia(concept, language="en")
        if result_en["exists"]:
            return {
                "exists": True,
                "source": "en-wiki",
                "url": result_en["url"],
                "summary": result_en["summary"][:200]
            }
        
        return {
            "exists": False,
            "source": None,
            "url": "",
            "summary": ""
        }
    
    async def search_arxiv(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        在Arxiv中搜索相关论文
        
        Args:
            query: 搜索查询
            max_results: 最大返回结果数
            
        Returns:
            [
                {
                    "title": 标题,
                    "authors": [作者列表],
                    "summary": 摘要,
                    "published": 发表日期,
                    "link": 链接,
                    "categories": [分类]
                },
                ...
            ]
        """
        try:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            response_text = await self._fetch_with_retry(
                self.arxiv_api_url,
                params=params
            )
            
            if not response_text:
                return []
            
            # 解析Arxiv的Atom XML响应
            papers = self._parse_arxiv_xml(response_text)
            
            logger.info(f"Found {len(papers)} papers for '{query}'")
            return papers
            
        except Exception as e:
            logger.error(f"Failed to search Arxiv: {e}")
            return []
    
    def _parse_arxiv_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        解析Arxiv的XML响应
        
        Args:
            xml_text: XML文本
            
        Returns:
            论文列表
        """
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_text)
            
            # Atom命名空间
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            papers = []
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                published = entry.find('atom:published', ns)
                link = entry.find('atom:id', ns)
                
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None:
                        authors.append(name.text.strip())
                
                categories = []
                for category in entry.findall('atom:category', ns):
                    term = category.get('term')
                    if term:
                        categories.append(term)
                
                paper = {
                    "title": title.text.strip() if title is not None else "",
                    "authors": authors,
                    "summary": summary.text.strip() if summary is not None else "",
                    "published": published.text.strip() if published is not None else "",
                    "link": link.text.strip() if link is not None else "",
                    "categories": categories
                }
                
                papers.append(paper)
            
            return papers
            
        except Exception as e:
            logger.error(f"Failed to parse Arxiv XML: {e}")
            return []
    
    async def verify_relation(
        self,
        concept_a: str,
        concept_b: str,
        claimed_relation: str
    ) -> Dict[str, Any]:
        """
        验证两个概念之间的关联（用于知识校验）
        
        Args:
            concept_a: 概念A
            concept_b: 概念B
            claimed_relation: 声称的关联描述
            
        Returns:
            {
                "credibility": float,  # 可信度 [0-1]
                "evidence": [证据列表],
                "sources": [来源列表]
            }
        """
        evidence = []
        sources = []
        credibility = 0.0
        
        # 1. Wikipedia验证
        wiki_a = await self.verify_concept_exists(concept_a)
        wiki_b = await self.verify_concept_exists(concept_b)
        
        if wiki_a["exists"]:
            evidence.append({
                "source": f"Wikipedia ({wiki_a['source']})",
                "url": wiki_a["url"],
                "snippet": wiki_a["summary"]
            })
            sources.append(wiki_a["source"])
            credibility += 0.3
        
        if wiki_b["exists"]:
            evidence.append({
                "source": f"Wikipedia ({wiki_b['source']})",
                "url": wiki_b["url"],
                "snippet": wiki_b["summary"]
            })
            sources.append(wiki_b["source"])
            credibility += 0.3
        
        # 2. Arxiv验证
        # 搜索同时包含两个概念的论文
        query = f"{concept_a} {concept_b}"
        papers = await self.search_arxiv(query, max_results=3)
        
        if papers:
            for paper in papers[:2]:  # 最多取2篇
                evidence.append({
                    "source": "Arxiv",
                    "url": paper["link"],
                    "snippet": f"{paper['title']} - {paper['summary'][:150]}..."
                })
                sources.append("arxiv")
            
            credibility += min(0.4, len(papers) * 0.1)
        
        # 限制在[0, 1]范围
        credibility = min(1.0, credibility)
        
        return {
            "credibility": credibility,
            "evidence": evidence,
            "sources": list(set(sources)),
            "verified": credibility >= 0.5
        }
    
    async def batch_verify(
        self,
        concepts: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量验证概念是否存在
        
        Args:
            concepts: 概念列表
            
        Returns:
            {概念: 验证结果, ...}
        """
        tasks = [self.verify_concept_exists(concept) for concept in concepts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        verified = {}
        for concept, result in zip(concepts, results):
            if isinstance(result, Exception):
                logger.error(f"Verification failed for {concept}: {result}")
                verified[concept] = {
                    "exists": False,
                    "source": None,
                    "url": "",
                    "summary": ""
                }
            else:
                verified[concept] = result
        
        return verified
    
    async def enrich_concept_data(
        self,
        concept: str,
        discipline: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        丰富概念数据（综合Wikipedia和Arxiv信息）
        
        Args:
            concept: 概念名称
            discipline: 学科（可选）
            
        Returns:
            {
                "concept": str,
                "definition": str,
                "wiki_exists": bool,
                "wiki_url": str,
                "related_papers": int,
                "credibility": float,
                "sources": [来源列表]
            }
        """
        # 1. Wikipedia数据
        wiki_result = await self.verify_concept_exists(concept)
        
        # 2. Arxiv数据
        arxiv_query = f"{concept} {discipline}" if discipline else concept
        papers = await self.search_arxiv(arxiv_query, max_results=5)
        
        # 3. 计算可信度
        credibility = 0.0
        if wiki_result["exists"]:
            credibility += 0.6
        
        if papers:
            credibility += min(0.4, len(papers) * 0.08)
        
        sources = []
        if wiki_result["exists"]:
            sources.append(wiki_result["source"])
        if papers:
            sources.append("arxiv")
        
        return {
            "concept": concept,
            "definition": wiki_result.get("summary", ""),
            "wiki_exists": wiki_result["exists"],
            "wiki_url": wiki_result.get("url", ""),
            "related_papers": len(papers),
            "paper_links": [p["link"] for p in papers[:3]],
            "credibility": credibility,
            "sources": sources
        }
