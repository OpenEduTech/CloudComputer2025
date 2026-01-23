"""
PatPat-Inconsistency-Hunter 溯源校验模块
负责验证冲突事实，尝试确定正确的事实
优化版本 - 支持多源验证、图片事实处理和增强的置信度评估
"""

import asyncio
import re
from typing import List, Optional, Dict, Any, Tuple

from ..config import settings
from ..models.schemas import (
    FactWithSource,
    ConflictPair,
    VerificationResult,
    VerificationResponse,
    ConflictReport,
)
from ..utils.logger import logger
from .llm_client import DeepSeekClient, get_llm_client
from .prompts import (
    FACT_VERIFICATION_SYSTEM_PROMPT,
    FACT_VERIFICATION_USER_PROMPT,
)


class FactVerifier:
    """
    事实验证器
    
    负责验证冲突事实，分析哪个事实更可能正确，并提供修正建议
    """
    
    def __init__(
        self,
        llm_client: Optional[DeepSeekClient] = None,
        max_concurrency: int = 3,
    ):
        """
        初始化事实验证器
        
        Args:
            llm_client: LLM客户端实例
            max_concurrency: 最大并发数
        """
        self._client = llm_client or get_llm_client()
        self._max_concurrency = max_concurrency
    
    async def verify_conflict(
        self,
        conflict: ConflictPair,
        context: str = "",
    ) -> VerificationResult:
        """
        验证单个冲突（增强版）
        
        使用多种策略验证：
        1. LLM 推理验证
        2. 来源可靠性评估
        3. 图片事实特殊处理
        4. 一致性交叉验证
        
        Args:
            conflict: 冲突对
            context: 文档上下文（可选，用于辅助判断）
        
        Returns:
            验证结果
        """
        # 预分析：检查是否涉及图片事实
        is_image_conflict = (
            conflict.fact_a.fact_type.startswith("image_") or
            conflict.fact_b.fact_type.startswith("image_")
        )
        
        # 预分析：评估来源可靠性
        reliability_a = self._assess_source_reliability(conflict.fact_a)
        reliability_b = self._assess_source_reliability(conflict.fact_b)
        
        # 构建增强的上下文
        enhanced_context = self._build_enhanced_context(
            conflict, context, is_image_conflict, reliability_a, reliability_b
        )
        
        messages = [
            {"role": "system", "content": FACT_VERIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": FACT_VERIFICATION_USER_PROMPT.format(
                conflict_type=conflict.conflict_type.value,
                conflict_description=conflict.description,
                fact_a_content=conflict.fact_a.content,
                fact_a_location=conflict.fact_a.location_description,
                fact_a_source=conflict.fact_a.source_text,
                fact_b_content=conflict.fact_b.content,
                fact_b_location=conflict.fact_b.location_description,
                fact_b_source=conflict.fact_b.source_text,
                context=enhanced_context,
            )},
        ]
        
        try:
            response = await self._client.chat_structured(
                messages=messages,
                response_model=VerificationResponse,
            )
            
            # 调整置信度：结合来源可靠性
            adjusted_confidence = self._adjust_confidence(
                response.confidence,
                reliability_a,
                reliability_b,
                response.correct_fact,
                conflict,
            )
            
            # 构建来源描述
            source_desc = response.source_description or ""
            if is_image_conflict:
                source_desc = f"[图文冲突] {source_desc}"
            
            return VerificationResult(
                conflict_id=conflict.conflict_id,
                is_verified=response.is_verified,
                correct_fact=response.correct_fact,
                source_url=None,
                source_description=source_desc,
                verification_reasoning=response.reasoning,
                confidence=adjusted_confidence,
            )
            
        except Exception as e:
            logger.error(f"验证冲突 {conflict.conflict_id} 失败: {e}")
            return VerificationResult(
                conflict_id=conflict.conflict_id,
                is_verified=False,
                correct_fact=None,
                source_url=None,
                source_description=None,
                verification_reasoning=f"验证过程出错: {str(e)}",
                confidence=0.0,
            )
    
    def _assess_source_reliability(self, fact: FactWithSource) -> float:
        """
        评估事实来源的可靠性
        
        Args:
            fact: 事实
            
        Returns:
            可靠性评分 (0-1)
        """
        score = 0.5  # 基础分
        
        # 图片来源的数据通常更可靠（表格、图表）
        if fact.fact_type.startswith("image_"):
            score += 0.15
        
        # 检查来源文本的特征
        source = fact.source_text.lower()
        
        # 正式表述加分
        formal_indicators = ["根据", "统计", "报告", "数据", "显示", "表明"]
        for indicator in formal_indicators:
            if indicator in source:
                score += 0.05
                break
        
        # 模糊表述减分
        vague_indicators = ["大约", "左右", "可能", "预计", "估计"]
        for indicator in vague_indicators:
            if indicator in source:
                score -= 0.1
                break
        
        # 位置靠前通常更正式
        if fact.source_position[0] < 1000:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _build_enhanced_context(
        self,
        conflict: ConflictPair,
        base_context: str,
        is_image_conflict: bool,
        reliability_a: float,
        reliability_b: float,
    ) -> str:
        """构建增强的验证上下文"""
        parts = []
        
        if base_context:
            parts.append(base_context)
        
        # 添加可靠性评估信息
        parts.append(f"\n\n## 来源可靠性评估")
        parts.append(f"- 事实A来源可靠性: {reliability_a:.0%}")
        parts.append(f"- 事实B来源可靠性: {reliability_b:.0%}")
        
        if is_image_conflict:
            parts.append("\n## 图文冲突说明")
            parts.append("此冲突涉及图片来源的数据。通常情况下：")
            parts.append("- 图表中的精确数据比文字描述更可靠")
            parts.append("- 表格数据通常经过校验")
            parts.append("- 但要注意图片可能有标注错误")
        
        return "\n".join(parts) if parts else "无额外上下文信息"
    
    def _adjust_confidence(
        self,
        base_confidence: float,
        reliability_a: float,
        reliability_b: float,
        correct_fact: Optional[str],
        conflict: ConflictPair,
    ) -> float:
        """
        调整置信度
        
        根据来源可靠性差异调整 LLM 给出的置信度
        """
        if not correct_fact:
            return base_confidence
        
        # 如果选择了更可靠来源的事实，增加置信度
        # 如果选择了不太可靠来源的事实，降低置信度
        
        # 判断选择的是哪个事实
        fact_a_selected = correct_fact in conflict.fact_a.content
        
        if fact_a_selected:
            reliability_selected = reliability_a
            reliability_other = reliability_b
        else:
            reliability_selected = reliability_b
            reliability_other = reliability_a
        
        reliability_diff = reliability_selected - reliability_other
        
        # 根据可靠性差异调整
        adjusted = base_confidence + (reliability_diff * 0.2)
        
        return max(0.1, min(0.99, adjusted))
    
    async def verify_conflicts(
        self,
        conflicts: List[ConflictPair],
        document_content: str = "",
        progress_callback: Optional[callable] = None,
    ) -> List[ConflictReport]:
        """
        批量验证冲突
        
        Args:
            conflicts: 冲突列表
            document_content: 文档内容（用于提供上下文）
            progress_callback: 进度回调函数
        
        Returns:
            带验证结果的冲突报告列表
        """
        if not conflicts:
            return []
        
        logger.info(f"开始验证 {len(conflicts)} 个冲突...")
        
        semaphore = asyncio.Semaphore(self._max_concurrency)
        completed = 0
        
        async def verify_single(conflict: ConflictPair) -> ConflictReport:
            nonlocal completed
            async with semaphore:
                # 获取冲突相关的上下文
                context = self._extract_relevant_context(
                    conflict, document_content
                )
                verification = await self.verify_conflict(conflict, context)
                completed += 1
                if progress_callback:
                    await progress_callback(completed / len(conflicts) * 100)
                return ConflictReport(
                    conflict=conflict,
                    verification=verification,
                )
        
        # 并行验证
        tasks = [verify_single(conflict) for conflict in conflicts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        reports = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"验证任务失败: {result}")
                # 创建一个无验证结果的报告
                reports.append(ConflictReport(
                    conflict=conflicts[i],
                    verification=None,
                ))
            else:
                reports.append(result)
        
        # 统计验证结果
        verified_count = sum(1 for r in reports if r.verification and r.verification.is_verified)
        logger.info(f"冲突验证完成，成功验证 {verified_count}/{len(conflicts)} 个冲突")
        
        return reports
    
    def _extract_relevant_context(
        self,
        conflict: ConflictPair,
        document_content: str,
        context_window: int = 500,
    ) -> str:
        """
        提取与冲突相关的文档上下文
        
        Args:
            conflict: 冲突对
            document_content: 文档内容
            context_window: 上下文窗口大小（字符数）
        
        Returns:
            相关上下文字符串
        """
        if not document_content:
            return ""
        
        contexts = []
        
        # 获取事实A周围的上下文
        pos_a = conflict.fact_a.source_position
        start_a = max(0, pos_a[0] - context_window)
        end_a = min(len(document_content), pos_a[1] + context_window)
        context_a = document_content[start_a:end_a]
        contexts.append(f"事实A的上下文:\n{context_a}")
        
        # 获取事实B周围的上下文
        pos_b = conflict.fact_b.source_position
        start_b = max(0, pos_b[0] - context_window)
        end_b = min(len(document_content), pos_b[1] + context_window)
        context_b = document_content[start_b:end_b]
        contexts.append(f"事实B的上下文:\n{context_b}")
        
        return "\n\n".join(contexts)
    
    async def analyze_conflict_severity(
        self,
        conflict: ConflictPair,
    ) -> Dict[str, Any]:
        """
        分析冲突的严重程度和影响
        
        Args:
            conflict: 冲突对
        
        Returns:
            严重程度分析结果
        """
        severity = conflict.severity
        
        # 根据严重程度给出级别
        if severity >= 0.9:
            level = "critical"
            level_cn = "严重"
            recommendation = "必须立即修正，该冲突可能导致严重误解"
        elif severity >= 0.6:
            level = "high"
            level_cn = "较高"
            recommendation = "建议尽快修正，该冲突可能影响文档可信度"
        elif severity >= 0.3:
            level = "medium"
            level_cn = "中等"
            recommendation = "建议关注并在后续修订中处理"
        else:
            level = "low"
            level_cn = "轻微"
            recommendation = "可视情况决定是否修正"
        
        return {
            "severity_score": severity,
            "severity_level": level,
            "severity_level_cn": level_cn,
            "recommendation": recommendation,
            "conflict_type": conflict.conflict_type.value,
            "conflict_description": conflict.description,
        }
    
    async def generate_correction_suggestion(
        self,
        conflict_report: ConflictReport,
    ) -> str:
        """
        生成冲突修正建议
        
        Args:
            conflict_report: 冲突报告
        
        Returns:
            修正建议文本
        """
        conflict = conflict_report.conflict
        verification = conflict_report.verification
        
        suggestions = []
        suggestions.append(f"## 冲突修正建议\n")
        suggestions.append(f"**冲突类型**: {conflict.conflict_type.value}")
        suggestions.append(f"**严重程度**: {conflict.severity:.0%}")
        suggestions.append(f"\n### 冲突描述")
        suggestions.append(conflict.description)
        
        suggestions.append(f"\n### 涉及的事实")
        suggestions.append(f"- **事实A** ({conflict.fact_a.location_description}): {conflict.fact_a.content}")
        suggestions.append(f"- **事实B** ({conflict.fact_b.location_description}): {conflict.fact_b.content}")
        
        if conflict.suggestion:
            suggestions.append(f"\n### 系统建议")
            suggestions.append(conflict.suggestion)
        
        if verification and verification.is_verified:
            suggestions.append(f"\n### 验证结果")
            suggestions.append(f"**置信度**: {verification.confidence:.0%}")
            if verification.correct_fact:
                suggestions.append(f"**建议采用**: {verification.correct_fact}")
            suggestions.append(f"\n**分析过程**:")
            suggestions.append(verification.verification_reasoning)
        
        return "\n".join(suggestions)

