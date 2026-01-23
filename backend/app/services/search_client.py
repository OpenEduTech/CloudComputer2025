# -*- coding: utf-8 -*-
"""
Search Client Service
Wrapper for Search APIs (Tavily, Serper)
Includes a Mock mode for testing without API keys.
"""
import os
import httpx
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SearchClient:
    """
    Search Client that supports Tavily, Serper, or a Mock fallback.
    Prioritizes TAVILY_API_KEY, then SERPER_API_KEY.
    """
    
    def __init__(self):
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.serper_key = os.getenv("SERPER_API_KEY")
        
        self.provider = "mock"
        if self.tavily_key:
            self.provider = "tavily"
        elif self.serper_key:
            self.provider = "serper"
            
        logger.info(f"SearchClient initialized with provider: {self.provider}")

    async def search(self, query: str, max_results: int = 3) -> List[str]:
        """
        Execute search and return a list of snippets/summaries.
        """
        if self.provider == "tavily":
            return await self._search_tavily(query, max_results)
        elif self.provider == "serper":
            return await self._search_serper(query, max_results)
        else:
            return await self._search_mock_with_llm(query)

    async def _search_tavily(self, query: str, max_results: int) -> List[str]:
        """Search using Tavily API"""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for result in data.get("results", []):
                    title = result.get("title", "")
                    content = result.get("content", "")
                    url = result.get("url", "")
                    results.append(f"Title: {title}\nSource: {url}\nContent: {content}")
                return results
        except Exception as e:
            logger.error(f"Tavily search failed: {str(e)}")
            return [f"[Search Error] Failed to search for '{query}' using Tavily."]

    async def _search_serper(self, query: str, max_results: int) -> List[str]:
        """Search using Serper API"""
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_key,
            "Content-Type": "application/json"
        }
        payload = json.dumps({
            "q": query,
            "num": max_results
        })
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, data=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for result in data.get("organic", []):
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    link = result.get("link", "")
                    results.append(f"Title: {title}\nSource: {link}\nContent: {snippet}")
                return results
        except Exception as e:
            logger.error(f"Serper search failed: {str(e)}")
            return [f"[Search Error] Failed to search for '{query}' using Serper."]

    async def _search_mock_with_llm(self, query: str) -> List[str]:
        """
        Mock search by asking the LLM to hallucinate accurate search results.
        This allows the system to be tested end-to-end using only the DeepSeek API Key.
        """
        logger.info(f"Performing LLM-based MOCK search for: {query}")
        
        # Local import to avoid circular dependency
        from app.services.llm_client import LLMClient
        llm = LLMClient()
        
        if not llm.is_available():
            return [
                f"[Search Error] LLM Key not configured, cannot simulate search results for '{query}'.",
                "Please configure DEEPSEEK_API_KEY to use this feature."
            ]

        prompt = f"""
        请模拟搜索引擎的功能。针对查询 "{query}"，请生成 3 个看起来真实的搜索结果摘要。
        
        要求：
        1. 内容必须是准确、客观的事实（基于你自己的知识库2023年截止的信息）。
        2. 如果查询包含明显的事实错误（例如"Python是2025年发布的"），搜索结果应该包含正确的信息（例如"Python发布于1991年"）以供后续纠错。
        3. 格式：
        Title: [标题]
        Source: [模拟的URL]
        Content: [摘要内容]
        
        请直接返回三个结果，用三个破折号 "---" 分隔。
        """
        
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await llm.chat(messages)
            if not response:
                return ["Mock search failed to generate content."]
            
            # Split by separator
            results = [r.strip() for r in response.split('---') if r.strip()]
            return results
        except Exception as e:
            logger.error(f"LLM Mock search failed: {e}")
            return [f"Mock search error: {e}"]

    def _search_mock(self, query: str) -> List[str]:
        """Legacy mock search (Unused now, kept for reference)"""
        return []
