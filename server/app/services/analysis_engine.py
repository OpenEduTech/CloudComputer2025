"""
PatPat-Inconsistency-Hunter 分析引擎
整合所有服务模块，提供完整的文档分析流程
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from collections import Counter

from ..config import settings
from ..models.schemas import (
    DocumentInput,
    AnalysisTask,
    AnalysisResult,
    TaskStatus,
    ConflictReport,
    FactWithSource,
)
from ..utils.logger import logger
from .document_processor import DocumentProcessor
from .fact_extractor import FactExtractor
from .conflict_detector import ConflictDetector
from .fact_verifier import FactVerifier
from .llm_client import DeepSeekClient, get_llm_client


class AnalysisEngine:
    """
    分析引擎
    
    整合文档处理、事实提取、冲突检测和验证的完整分析流程
    """
    
    def __init__(
        self,
        llm_client: Optional[DeepSeekClient] = None,
        max_concurrency: int = 5,
    ):
        """
        初始化分析引擎
        
        Args:
            llm_client: LLM客户端实例
            max_concurrency: 最大并发数
        """
        self._client = llm_client or get_llm_client()
        self._max_concurrency = max_concurrency
        
        # 初始化各个处理模块
        self._document_processor = DocumentProcessor(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        self._fact_extractor = FactExtractor(
            llm_client=self._client,
            max_concurrency=max_concurrency,
        )
        self._conflict_detector = ConflictDetector(
            llm_client=self._client,
            max_concurrency=max_concurrency,
        )
        self._fact_verifier = FactVerifier(
            llm_client=self._client,
            max_concurrency=max_concurrency,
        )
        
        # 任务状态存储（实际应用中应使用Redis）
        self._tasks: Dict[str, AnalysisTask] = {}
    
    async def analyze_document(
        self,
        document: DocumentInput,
        task_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
        skip_verification: bool = False,
    ) -> AnalysisResult:
        """
        执行完整的文档分析流程
        
        Args:
            document: 文档输入
            task_id: 任务ID（可选）
            progress_callback: 进度回调函数 (task_id, progress, step_description)
            skip_verification: 是否跳过验证步骤
        
        Returns:
            完整的分析结果
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        
        # 创建任务
        task = AnalysisTask(
            task_id=task_id,
            status=TaskStatus.PENDING,
            progress=0.0,
            current_step="初始化",
        )
        self._tasks[task_id] = task
        
        async def update_progress(progress: float, step: str):
            task.progress = progress
            task.current_step = step
            task.updated_at = datetime.now()
            if progress_callback:
                await progress_callback(task_id, progress, step)
        
        try:
            # ===== 第一步：验证文档 =====
            await update_progress(5, "验证文档")
            is_valid, error_msg = self._document_processor.validate_document(document)
            if not is_valid:
                raise ValueError(error_msg)
            
            # ===== 第二步：处理文档 =====
            await update_progress(10, "处理文档结构")
            chunks, metadata = self._document_processor.process_document(document)
            
            if not chunks:
                raise ValueError("文档分块失败，无法提取有效内容")
            
            logger.info(f"文档处理完成: {len(chunks)} 个分块")
            
            # ===== 第三步：提取事实 =====
            task.status = TaskStatus.EXTRACTING
            await update_progress(15, "提取事实")
            
            async def extraction_progress(p: float):
                await update_progress(15 + p * 0.35, f"提取事实 ({p:.0f}%)")
            
            facts = await self._fact_extractor.extract_and_filter(
                chunks=chunks,
                extraction_progress_callback=extraction_progress,
            )
            
            if not facts:
                logger.warning("未提取到任何事实")
                return self._create_empty_result(
                    task_id, document, metadata, time.time() - start_time
                )
            
            logger.info(f"提取到 {len(facts)} 个事实")
            
            # ===== 第四步：检测冲突 =====
            task.status = TaskStatus.DETECTING
            await update_progress(50, "检测冲突")
            
            async def detection_progress(p: float):
                await update_progress(50 + p * 0.25, f"检测冲突 ({p:.0f}%)")
            
            conflicts = await self._conflict_detector.detect_conflicts(
                facts=facts,
                progress_callback=detection_progress,
            )
            
            logger.info(f"检测到 {len(conflicts)} 个冲突")
            
            # ===== 第五步：验证冲突（可选） =====
            conflict_reports: List[ConflictReport] = []
            
            if conflicts and not skip_verification:
                task.status = TaskStatus.VERIFYING
                await update_progress(75, "验证冲突")
                
                async def verification_progress(p: float):
                    await update_progress(75 + p * 0.20, f"验证冲突 ({p:.0f}%)")
                
                conflict_reports = await self._fact_verifier.verify_conflicts(
                    conflicts=conflicts,
                    document_content=document.content,
                    progress_callback=verification_progress,
                )
            else:
                # 不进行验证，直接包装成报告
                conflict_reports = [
                    ConflictReport(conflict=c, verification=None)
                    for c in conflicts
                ]
            
            # ===== 第六步：生成结果 =====
            await update_progress(95, "生成报告")
            
            analysis_time = time.time() - start_time
            
            # 统计冲突类型分布
            conflict_type_distribution = dict(Counter(
                cr.conflict.conflict_type.value for cr in conflict_reports
            ))
            
            # 统计严重程度分布
            severity_distribution = {
                "critical": sum(1 for cr in conflict_reports if cr.conflict.severity >= 0.9),
                "high": sum(1 for cr in conflict_reports if 0.6 <= cr.conflict.severity < 0.9),
                "medium": sum(1 for cr in conflict_reports if 0.3 <= cr.conflict.severity < 0.6),
                "low": sum(1 for cr in conflict_reports if cr.conflict.severity < 0.3),
            }
            
            verified_count = sum(
                1 for cr in conflict_reports 
                if cr.verification and cr.verification.is_verified
            )
            
            result = AnalysisResult(
                task_id=task_id,
                document_title=metadata.get("title"),
                document_length=metadata.get("content_length", len(document.content)),
                total_chunks=len(chunks),
                total_facts=len(facts),
                total_conflicts=len(conflict_reports),
                verified_conflicts=verified_count,
                facts=facts,
                conflicts=conflict_reports,
                analysis_time=analysis_time,
                conflict_type_distribution=conflict_type_distribution,
                severity_distribution=severity_distribution,
            )
            
            # 更新任务状态
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.current_step = "完成"
            await update_progress(100, "分析完成")
            
            logger.info(
                f"文档分析完成: {result.total_facts} 个事实, "
                f"{result.total_conflicts} 个冲突, "
                f"耗时 {analysis_time:.2f}秒"
            )
            
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.current_step = "失败"
            logger.error(f"文档分析失败: {e}")
            raise
    
    def _create_empty_result(
        self,
        task_id: str,
        document: DocumentInput,
        metadata: Dict[str, Any],
        analysis_time: float,
    ) -> AnalysisResult:
        """
        创建空结果（当未提取到事实时）
        
        Args:
            task_id: 任务ID
            document: 文档输入
            metadata: 文档元信息
            analysis_time: 分析耗时
        
        Returns:
            空的分析结果
        """
        return AnalysisResult(
            task_id=task_id,
            document_title=metadata.get("title"),
            document_length=len(document.content),
            total_chunks=metadata.get("total_chunks", 0),
            total_facts=0,
            total_conflicts=0,
            verified_conflicts=0,
            facts=[],
            conflicts=[],
            analysis_time=analysis_time,
            conflict_type_distribution={},
            severity_distribution={},
        )
    
    def get_task(self, task_id: str) -> Optional[AnalysisTask]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态或None
        """
        return self._tasks.get(task_id)
    
    def list_tasks(self) -> List[AnalysisTask]:
        """
        列出所有任务
        
        Returns:
            任务列表
        """
        return list(self._tasks.values())
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功取消
        """
        task = self._tasks.get(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.EXTRACTING, 
                                     TaskStatus.DETECTING, TaskStatus.VERIFYING]:
            task.status = TaskStatus.FAILED
            task.error_message = "用户取消"
            return True
        return False


# 创建全局分析引擎实例
_engine_instance: Optional[AnalysisEngine] = None


def get_analysis_engine() -> AnalysisEngine:
    """获取分析引擎单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AnalysisEngine()
    return _engine_instance


# ==================== LangGraph 增强引擎 ====================

def get_enhanced_analysis_engine():
    """
    获取增强版分析引擎（使用 LangGraph）
    
    增强版特性：
    - 支持图片内容提取和分析
    - 更智能的候选对生成
    - 并行处理优化
    - 更完备的冲突检测
    """
    try:
        from .langgraph_engine import get_langgraph_engine
        return get_langgraph_engine()
    except ImportError as e:
        logger.warning(f"LangGraph 引擎不可用，使用基础引擎: {e}")
        return get_analysis_engine()
