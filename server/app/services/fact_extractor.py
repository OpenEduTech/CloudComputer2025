"""
PatPat-Inconsistency-Hunter 事实提取模块
负责从长文档中提取关键事实
"""

import asyncio
import uuid
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

from ..config import settings
from ..models.schemas import (
    DocumentChunk,
    FactWithSource,
    FactExtractionResponse,
)
from ..utils.logger import logger
from .llm_client import DeepSeekClient, get_llm_client
from .prompts import (
    FACT_EXTRACTION_SYSTEM_PROMPT,
    FACT_EXTRACTION_USER_PROMPT,
    FACT_FILTER_SYSTEM_PROMPT,
    FACT_FILTER_USER_PROMPT,
)


class FactFilterResponse(BaseModel):
    """事实过滤响应模型"""
    reasoning: str = Field(..., description="判断理由")
    determination: str = Field(..., description="判断结果: worthy 或 not_worthy")


class FactExtractor:
    """
    事实提取器
    
    负责从文档分块中提取原子事实，并进行过滤筛选
    """
    
    def __init__(
        self,
        llm_client: Optional[DeepSeekClient] = None,
        max_concurrency: int = 5,
    ):
        """
        初始化事实提取器
        
        Args:
            llm_client: LLM客户端实例
            max_concurrency: 最大并发数
        """
        self._client = llm_client or get_llm_client()
        self._max_concurrency = max_concurrency
    
    async def extract_facts_from_chunk(
        self,
        chunk: DocumentChunk,
    ) -> List[FactWithSource]:
        """
        从单个文档分块中提取事实
        
        Args:
            chunk: 文档分块
        
        Returns:
            提取的事实列表
        """
        # 构建提取消息
        messages = [
            {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": FACT_EXTRACTION_USER_PROMPT.format(
                chapter=chunk.chapter or "未知",
                section=chunk.section or "未知",
                content=chunk.content,
            )},
        ]
        
        try:
            # 调用LLM提取事实
            response = await self._client.chat_structured(
                messages=messages,
                response_model=FactExtractionResponse,
            )
            
            # 转换为FactWithSource格式
            facts = []
            for fact_item in response.facts:
                fact = FactWithSource(
                    fact_id=f"fact_{uuid.uuid4().hex[:12]}",
                    content=fact_item.content,
                    fact_type=fact_item.fact_type,
                    confidence=fact_item.confidence,
                    source_chunk_id=chunk.chunk_id,
                    source_text=fact_item.source_text,
                    source_position=(chunk.start_position, chunk.end_position),
                    chapter=chunk.chapter,
                    section=chunk.section,
                )
                facts.append(fact)
            
            logger.info(f"从分块 {chunk.chunk_id} 提取了 {len(facts)} 个事实")
            return facts
            
        except Exception as e:
            logger.error(f"从分块 {chunk.chunk_id} 提取事实失败: {e}")
            return []
    
    async def extract_facts_from_chunks(
        self,
        chunks: List[DocumentChunk],
        progress_callback: Optional[callable] = None,
    ) -> List[FactWithSource]:
        """
        从多个文档分块中并行提取事实
        
        Args:
            chunks: 文档分块列表
            progress_callback: 进度回调函数
        
        Returns:
            所有提取的事实列表
        """
        if not chunks:
            return []
        
        logger.info(f"开始从 {len(chunks)} 个分块中提取事实...")
        
        # 使用信号量限制并发
        semaphore = asyncio.Semaphore(self._max_concurrency)
        completed = 0
        
        async def extract_with_semaphore(chunk: DocumentChunk) -> List[FactWithSource]:
            nonlocal completed
            async with semaphore:
                result = await self.extract_facts_from_chunk(chunk)
                completed += 1
                if progress_callback:
                    await progress_callback(completed / len(chunks) * 100)
                return result
        
        # 并行提取
        tasks = [extract_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_facts = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"事实提取任务失败: {result}")
                continue
            all_facts.extend(result)
        
        # 去重
        all_facts = self._deduplicate_facts(all_facts)
        
        logger.info(f"事实提取完成，共提取 {len(all_facts)} 个唯一事实")
        return all_facts
    
    async def filter_facts(
        self,
        facts: List[FactWithSource],
        progress_callback: Optional[callable] = None,
    ) -> List[FactWithSource]:
        """
        过滤不需要检验的事实
        
        Args:
            facts: 事实列表
            progress_callback: 进度回调函数
        
        Returns:
            过滤后的事实列表
        """
        if not facts:
            return []
        
        logger.info(f"开始过滤 {len(facts)} 个事实...")
        
        semaphore = asyncio.Semaphore(self._max_concurrency)
        completed = 0
        
        async def filter_single_fact(fact: FactWithSource) -> Optional[FactWithSource]:
            nonlocal completed
            async with semaphore:
                is_worthy = await self._is_fact_worthy(fact)
                completed += 1
                if progress_callback:
                    await progress_callback(completed / len(facts) * 100)
                return fact if is_worthy else None
        
        # 并行过滤
        tasks = [filter_single_fact(fact) for fact in facts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集通过过滤的事实
        filtered_facts = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"事实过滤任务失败: {result}")
                continue
            if result is not None:
                filtered_facts.append(result)
        
        logger.info(f"事实过滤完成，保留 {len(filtered_facts)} 个事实（过滤了 {len(facts) - len(filtered_facts)} 个）")
        return filtered_facts
    
    async def _is_fact_worthy(self, fact: FactWithSource) -> bool:
        """
        判断事实是否值得检验
        
        Args:
            fact: 事实
        
        Returns:
            是否值得检验
        """
        messages = [
            {"role": "system", "content": FACT_FILTER_SYSTEM_PROMPT},
            {"role": "user", "content": FACT_FILTER_USER_PROMPT.format(
                fact_content=fact.content,
                fact_type=fact.fact_type,
                source_text=fact.source_text,
            )},
        ]
        
        try:
            response = await self._client.chat_structured(
                messages=messages,
                response_model=FactFilterResponse,
            )
            return response.determination == "worthy"
        except Exception as e:
            logger.warning(f"事实过滤失败，默认保留: {e}")
            return True  # 失败时默认保留
    
    def _deduplicate_facts(self, facts: List[FactWithSource]) -> List[FactWithSource]:
        """
        对事实进行去重
        
        Args:
            facts: 事实列表
        
        Returns:
            去重后的事实列表
        """
        seen_contents = set()
        unique_facts = []
        
        for fact in facts:
            # 使用事实内容的标准化形式作为去重键
            normalized_content = fact.content.strip().lower()
            if normalized_content not in seen_contents:
                seen_contents.add(normalized_content)
                unique_facts.append(fact)
        
        return unique_facts
    
    async def extract_and_filter(
        self,
        chunks: List[DocumentChunk],
        extraction_progress_callback: Optional[callable] = None,
        filter_progress_callback: Optional[callable] = None,
    ) -> List[FactWithSource]:
        """
        提取并过滤事实（完整流程）
        
        Args:
            chunks: 文档分块列表
            extraction_progress_callback: 提取进度回调
            filter_progress_callback: 过滤进度回调
        
        Returns:
            最终的事实列表
        """
        # 第一步：提取事实
        all_facts = await self.extract_facts_from_chunks(
            chunks=chunks,
            progress_callback=extraction_progress_callback,
        )
        
        if not all_facts:
            logger.warning("未提取到任何事实")
            return []
        
        # 第二步：过滤事实
        filtered_facts = await self.filter_facts(
            facts=all_facts,
            progress_callback=filter_progress_callback,
        )
        
        return filtered_facts

