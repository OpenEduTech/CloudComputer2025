"""
事实提取服务
整合 LLM 和 Redis，提供完整的事实提取流程
"""
import asyncio
import uuid
import logging
from typing import List, Dict, Any, Optional, Callable

from .llm_client import llm_client
from .redis_client import redis_client
from .fact_schema import ensure_schema, enrich_location
from .progress_manager import progress_manager, ProgressStage

logger = logging.getLogger(__name__)


class FactExtractor:
    """事实提取器"""
    
    def __init__(self):
        self.llm = llm_client
        self.redis = redis_client
    
    async def extract_from_document(
        self,
        document_id: str,
        sections: List[Dict[str, Any]],
        filename: str = "",
        save_to_redis: bool = True,
        report_progress: bool = True
    ) -> Dict[str, Any]:
        """
        从文档中提取所有事实（支持超长文档分片处理）
        
        Args:
            document_id: 文档ID
            sections: 文档章节列表（来自 parser）
            filename: 文件名
            save_to_redis: 是否保存到 Redis
            report_progress: 是否报告进度
        
        Returns:
            提取结果，包含所有事实和统计信息
        """
        if not self.llm.is_available():
            raise ValueError("LLM 服务不可用，请检查 DEEPSEEK_API_KEY 配置")
        
        all_facts = []
        section_stats = []
        
        # 超长文档分片处理：对超过 3000 字的章节进行分片
        processed_sections = self._split_long_sections(sections)
        
        # 计算有效章节数（内容长度>=20的章节）
        valid_sections = [s for s in processed_sections if len(s.get("content", "")) >= 20]
        total_valid = len(valid_sections)
        
        logger.info(f"文档 {filename}: 原始章节数={len(sections)}, 分片后={len(processed_sections)}, 有效={total_valid}")
        processed_count = 0
        
        # 初始化进度
        if report_progress:
            await progress_manager.update_progress(
                document_id,
                stage=ProgressStage.EXTRACT_FACTS,
                stage_label="提取事实",
                current=0,
                total=total_valid,
                message=f"正在使用 LLM 提取关键事实 (0/{total_valid})",
                sub_message="准备中..."
            )
        
        # 并行化优化：批量处理章节
        batch_size = 5  # 每批并行处理5个章节
        
        for batch_start in range(0, len(sections), batch_size):
            batch = sections[batch_start:batch_start + batch_size]
            
            # 并行提取事实
            tasks = []
            for idx_in_batch, section in enumerate(batch):
                idx = batch_start + idx_in_batch
                section_title = section.get("title", "")
                section_content = section.get("content", "")
                
                if not section_content or len(section_content) < 20:
                    continue
                
                logger.info(f"正在提取章节 {idx + 1}/{len(sections)}: {section_title[:30]}...")
                tasks.append((idx, section_title, self.llm.extract_facts(
                    text=section_content,
                    section_title=section_title,
                    section_index=idx
                )))
            
            # 等待批次完成
            results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)
            
            # 处理结果
            for (idx, section_title, _), result in zip(tasks, results):
                processed_count += 1
                
                # 更新进度
                if report_progress:
                    await progress_manager.update_progress(
                        document_id,
                        current=processed_count,
                        total=total_valid,
                        message=f"正在使用 LLM 提取关键事实 ({processed_count}/{total_valid})",
                        sub_message=f"章节: {section_title[:40]}..." if len(section_title) > 40 else f"章节: {section_title}"
                    )
                
                if isinstance(result, Exception):
                    logger.error(f"章节 {idx} 提取失败: {str(result)}")
                    section_stats.append({
                        "section_index": idx,
                        "section_title": section_title,
                        "fact_count": 0,
                        "error": str(result)
                    })
                    continue
                
                # Post-process facts per section
                processed = []
                for f in result:
                    f = ensure_schema(f)
                    f = enrich_location(f, section_title, idx)
                    processed.append(f)
                
                # Deduplicate within this section
                processed = self._deduplicate_facts(processed)
                all_facts.extend(processed)
                section_stats.append({
                    "section_index": idx,
                    "section_title": section_title,
                    "fact_count": len(processed)
                })
        
        # 去重（基于内容包含关系），并生成唯一ID
        all_facts = self._deduplicate_facts(all_facts)
        for i, fact in enumerate(all_facts):
            fact["fact_id"] = f"{document_id}_{i}"
        
        # 统计信息
        stats = self._calculate_stats(all_facts)
        
        result = {
            "document_id": document_id,
            "filename": filename,
            "total_facts": len(all_facts),
            "facts": all_facts,
            "section_stats": section_stats,
            "statistics": stats
        }
        
        # 保存到 Redis
        if save_to_redis:
            try:
                self.redis.save_facts(document_id, all_facts)
                
                # Fetch existing metadata to preserve other fields (like word_count, original text)
                existing_meta = self.redis.get_document_metadata(document_id) or {}
                
                # Update with new extraction stats
                existing_meta.update({
                    "filename": filename,
                    "total_facts": len(all_facts),
                    "section_count": len(sections),
                    "statistics": stats,
                    "sections": sections # Ensure sections are preserved/updated
                })
                
                self.redis.save_document_metadata(document_id, existing_meta)
                result["saved_to_redis"] = True
            except Exception as e:
                logger.error(f"保存到 Redis 失败: {str(e)}")
                result["saved_to_redis"] = False
        
        return result
    
    def _split_long_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对超长章节进行分片处理，避免 LLM token 限制

        策略：
        - 单章节 > 3000 字：按段落分片，每片 ~2500 字
        - 保留上下文重叠（200字）以保证连贯性

        Args:
            sections: 原始章节列表

        Returns:
            分片后的章节列表
        """
        MAX_SECTION_LENGTH = 3000  # 单章节最大字数
        CHUNK_SIZE = 2500          # 分片大小
        OVERLAP = 200              # 重叠大小

        result = []

        for section in sections:
            content = section.get("content", "")
            title = section.get("title", "")
        
            if len(content) <= MAX_SECTION_LENGTH:
                # 章节不超长，直接保留
                result.append(section)
            else:
                # 超长章节，需要分片
                logger.info(f"检测到超长章节 '{title}' ({len(content)}字)，进行分片处理")
            
                # 按段落分割（保留空行为分割符）
                paragraphs = content.split('\n\n')
            
                chunks = []
                current_chunk = ""
            
                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue
                
                    # 如果当前块 + 新段落 > CHUNK_SIZE，则切换
                    if len(current_chunk) + len(para) > CHUNK_SIZE and current_chunk:
                        chunks.append(current_chunk)
                        # 保留重叠
                        current_chunk = current_chunk[-OVERLAP:] + "\n\n" + para
                    else:
                        current_chunk += ("\n\n" if current_chunk else "") + para
            
                # 添加最后一块
                if current_chunk:
                    chunks.append(current_chunk)
            
                # 生成分片章节
                for i, chunk in enumerate(chunks):
                    result.append({
                        "title": f"{title} [分片 {i+1}/{len(chunks)}]",
                        "content": chunk,
                        "level": section.get("level", 1),
                        "original_section": title,  # 记录原始章节名
                        "chunk_index": i
                    })
            
                logger.info(f"章节 '{title}' 分为 {len(chunks)} 片")

        return result
    
    def _deduplicate_facts(self, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove fragment facts when their content is contained in a longer one."""
        kept = []
        contents = [f.get("content", "") for f in facts]
        for i, f in enumerate(facts):
            c = contents[i]
            is_sub = False
            for j, other in enumerate(facts):
                if i == j:
                    continue
                oc = contents[j]
                if c and oc and c != oc and c in oc:
                    is_sub = True
                    break
            if not is_sub:
                kept.append(f)
        return kept

    def _calculate_stats(self, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算事实统计信息"""
        type_counts = {}
        total_confidence = 0
        
        for fact in facts:
            fact_type = fact.get("type", "未知")
            type_counts[fact_type] = type_counts.get(fact_type, 0) + 1
            total_confidence += fact.get("confidence", 0)
        
        avg_confidence = total_confidence / len(facts) if facts else 0
        
        return {
            "type_distribution": type_counts,
            "average_confidence": round(avg_confidence, 3)
        }
    
    def get_facts(self, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """从 Redis 获取文档事实"""
        return self.redis.get_facts(document_id)
    
    def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取文档信息"""
        return self.redis.get_document_metadata(document_id)


# 全局事实提取器实例
fact_extractor = FactExtractor()

