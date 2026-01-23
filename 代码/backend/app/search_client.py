import aiohttp
import asyncio
from typing import List, Dict, Any
import json
from urllib.parse import quote_plus
import requests

class SearchClient:
    def __init__(self):
        self.wikipedia_api = "https://en.wikipedia.org/api/rest_v1/page/summary/"
        self.arxiv_api = "http://export.arxiv.org/api/query"
        self.semantic_scholar_api = "https://api.semanticscholar.org/graph/v1/paper/search"
        
    async def search_external(self, query: str, sources: List[str] = None) -> Dict[str, Any]:
        """
        从多个外部源搜索相关信息
        """
        if sources is None:
            sources = ["wikipedia", "arxiv", "semantic_scholar"]
        
        # 并行搜索
        tasks = []
        if "wikipedia" in sources:
            tasks.append(self.search_wikipedia(query))
        if "arxiv" in sources:
            tasks.append(self.search_arxiv(query))
        if "semantic_scholar" in sources:
            tasks.append(self.search_semantic_scholar(query))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        combined_results = {
            "wikipedia": [],
            "arxiv": [],
            "semantic_scholar": [],
            "all_sources": []
        }
        
        for i, source in enumerate(sources):
            if i < len(results) and not isinstance(results[i], Exception):
                combined_results[source] = results[i]
                combined_results["all_sources"].extend(results[i][:3])  # 每个源取前3个
        
        # 按相关性排序（简单实现）
        combined_results["all_sources"] = sorted(
            combined_results["all_sources"],
            key=lambda x: x.get("relevance_score", 0),
            reverse=True
        )[:10]  # 限制总结果数
        
        return combined_results
    
    async def search_wikipedia(self, query: str) -> List[Dict]:
        """搜索Wikipedia"""
        url = f"{self.wikipedia_api}{quote_plus(query)}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [{
                            "source": "Wikipedia",
                            "title": data.get("title", ""),
                            "summary": data.get("extract", ""),
                            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                            "relevance_score": 0.9
                        }]
        except Exception as e:
            print(f"Wikipedia搜索错误: {e}")
        
        return []
    
    async def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict]:
        """搜索Arxiv学术论文"""
        params = {
            "search_query": f"all:{quote_plus(query)}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        url = f"{self.arxiv_api}?search_query={params['search_query']}&start={params['start']}&max_results={params['max_results']}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # 解析Atom格式（简化版）
                        results = []
                        lines = content.split('\n')
                        
                        entry = {}
                        for line in lines:
                            line = line.strip()
                            if line.startswith('<entry>'):
                                entry = {}
                            elif line.startswith('<title>'):
                                entry['title'] = line.replace('<title>', '').replace('</title>', '').strip()
                            elif line.startswith('<summary>'):
                                entry['summary'] = line.replace('<summary>', '').replace('</summary>', '').strip()
                            elif line.startswith('<id>'):
                                entry['url'] = line.replace('<id>', '').replace('</id>', '').strip()
                            elif line.startswith('</entry>'):
                                if entry:
                                    results.append({
                                        "source": "Arxiv",
                                        "title": entry.get('title', ''),
                                        "summary": entry.get('summary', '')[:200] + "...",
                                        "url": entry.get('url', ''),
                                        "relevance_score": 0.8
                                    })
                        
                        return results
        except Exception as e:
            print(f"Arxiv搜索错误: {e}")
        
        return []
    
    async def search_semantic_scholar(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索Semantic Scholar学术论文"""
        headers = {
            'User-Agent': 'PPT-Knowledge-Extender/1.0'
        }
        
        params = {
            'query': query,
            'limit': limit,
            'fields': 'title,abstract,url,year,authors,citationCount'
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(self.semantic_scholar_api, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        results = []
                        for paper in data.get('data', [])[:limit]:
                            authors = [author['name'] for author in paper.get('authors', [])[:3]]
                            
                            results.append({
                                "source": "Semantic Scholar",
                                "title": paper.get('title', ''),
                                "summary": paper.get('abstract', '')[:200] + "...",
                                "url": paper.get('url', ''),
                                "authors": authors,
                                "year": paper.get('year'),
                                "citations": paper.get('citationCount', 0),
                                "relevance_score": 0.85
                            })
                        
                        return results
        except Exception as e:
            print(f"Semantic Scholar搜索错误: {e}")
        
        return []
    
    async def search_multiple_sources_concurrently(self, queries: List[str]) -> Dict[str, List]:
        """
        并行搜索多个查询
        """
        tasks = [self.search_external(query) for query in queries]
        results = await asyncio.gather(*tasks)
        
        return dict(zip(queries, results))