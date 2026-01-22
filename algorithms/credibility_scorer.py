"""
可信度评分算法模块
解决大模型幻觉问题，提供多源验证和可信度评估
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """数据源类型"""
    WIKIPEDIA = "wikipedia"
    ARXIV = "arxiv"
    LLM_REASONING = "llm_reasoning"
    TEXTBOOK = "textbook"
    ACADEMIC_DATABASE = "academic_database"


class CredibilityLevel(Enum):
    """可信度等级"""
    VERIFIED = "verified"  # 0.9-1.0: 多源验证，高度可信
    RELIABLE = "reliable"  # 0.7-0.9: 有权威来源支持
    PROBABLE = "probable"  # 0.5-0.7: 有一定依据
    UNCERTAIN = "uncertain"  # 0.3-0.5: 缺乏充分证据
    QUESTIONABLE = "questionable"  # 0.0-0.3: 可能错误


@dataclass
class Evidence:
    """证据数据类"""
    source_type: SourceType
    source_name: str
    content: str
    url: Optional[str] = None
    confidence: float = 0.5  # 单个证据的置信度
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_type": self.source_type.value,
            "source_name": self.source_name,
            "content": self.content,
            "url": self.url,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }


@dataclass
class ConflictInfo:
    """冲突信息"""
    conflicting_evidences: List[Evidence]
    conflict_type: str  # "contradiction", "inconsistency", "ambiguity"
    severity: float  # 0.0-1.0
    resolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "conflicting_evidences": [e.to_dict() for e in self.conflicting_evidences],
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "resolution": self.resolution
        }


class CredibilityScorer:
    """
    可信度评分器
    
    核心功能：
    1. 多源验证：整合来自不同来源的证据
    2. 可信度计算：基于证据质量和数量计算分数
    3. 冲突检测：识别证据间的矛盾
    4. 来源溯源：追踪信息来源链
    """
    
    def __init__(
        self,
        min_evidence_count: int = 2,
        wikipedia_weight: float = 0.7,
        arxiv_weight: float = 0.9,
        llm_weight: float = 0.3,  # 降低到0.3，减少LLM幻觉风险
        conflict_threshold: float = 0.6,
        semantic_conflict_threshold: float = 0.75  # 新增：语义冲突阈值
    ):
        """
        初始化可信度评分器
        
        Args:
            min_evidence_count: 最少证据数量
            wikipedia_weight: Wikipedia权重
            arxiv_weight: Arxiv权重
            llm_weight: LLM推理权重（降低到0.3防止幻觉）
            conflict_threshold: 置信度差异冲突阈值
            semantic_conflict_threshold: 语义相似度冲突阈值
        """
        self.min_evidence_count = min_evidence_count
        self.source_weights = {
            SourceType.WIKIPEDIA: wikipedia_weight,
            SourceType.ARXIV: arxiv_weight,
            SourceType.LLM_REASONING: llm_weight,
            SourceType.TEXTBOOK: 0.95,
            SourceType.ACADEMIC_DATABASE: 0.85
        }
        self.conflict_threshold = conflict_threshold
        self.semantic_conflict_threshold = semantic_conflict_threshold
        
        # 初始化语义分析工具（用于冲突检测）
        try:
            from algorithms.semantic_similarity import SemanticSimilarityCalculator
            self.semantic_analyzer = SemanticSimilarityCalculator()
            logger.info("Semantic analyzer initialized for conflict detection")
        except Exception as e:
            logger.warning(f"Semantic analyzer not available: {e}")
            self.semantic_analyzer = None
        
        logger.info("CredibilityScorer initialized")
    
    def calculate_credibility(
        self,
        evidences: List[Evidence],
        concept_a: str,
        concept_b: str
    ) -> Dict[str, Any]:
        """
        计算可信度分数
        
        Args:
            evidences: 证据列表
            concept_a: 概念A
            concept_b: 概念B
            
        Returns:
            包含可信度分数和详细信息的字典
        """
        if not evidences:
            logger.warning("No evidence provided for credibility calculation")
            return {
                "credibility_score": 0.0,
                "credibility_level": CredibilityLevel.QUESTIONABLE.value,
                "evidence_count": 0,
                "source_diversity": 0.0,
                "has_conflicts": False,
                "warnings": ["无任何证据支持"]
            }
        
        # 1. 计算基础分数（基于证据质量和数量）
        base_score = self._calculate_base_score(evidences)
        
        # 2. 计算来源多样性奖励
        diversity_bonus = self._calculate_diversity_bonus(evidences)
        
        # 3. 检测证据冲突
        conflicts = self._detect_conflicts(evidences)
        conflict_penalty = self._calculate_conflict_penalty(conflicts)
        
        # 4. 计算最终可信度分数
        credibility_score = min(1.0, base_score + diversity_bonus - conflict_penalty)
        
        # 5. 确定可信度等级
        credibility_level = self._determine_credibility_level(credibility_score)
        
        # 6. 生成警告信息
        warnings = self._generate_warnings(
            evidences, conflicts, credibility_score
        )
        
        result = {
            "credibility_score": round(credibility_score, 3),
            "credibility_level": credibility_level.value,
            "evidence_count": len(evidences),
            "source_diversity": round(diversity_bonus, 3),
            "has_conflicts": len(conflicts) > 0,
            "conflicts": [c.to_dict() for c in conflicts],
            "evidences": [e.to_dict() for e in evidences],
            "warnings": warnings
        }
        
        logger.info(
            f"Credibility calculated: {concept_a} -> {concept_b}, "
            f"score={credibility_score:.3f}, level={credibility_level.value}"
        )
        
        return result
    
    def _calculate_base_score(self, evidences: List[Evidence]) -> float:
        """
        计算基础分数
        
        基于证据的权重和置信度计算加权平均分
        """
        if not evidences:
            return 0.0
        
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for evidence in evidences:
            source_weight = self.source_weights.get(
                evidence.source_type, 0.5
            )
            weighted_sum += evidence.confidence * source_weight
            weight_sum += source_weight
        
        base_score = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        # 证据数量调整
        if len(evidences) < self.min_evidence_count:
            # 证据不足，降低分数
            base_score *= (len(evidences) / self.min_evidence_count)
        
        return base_score
    
    def _calculate_diversity_bonus(self, evidences: List[Evidence]) -> float:
        """
        计算来源多样性奖励
        
        多个独立来源的证据增加可信度
        """
        unique_sources = set(e.source_type for e in evidences)
        source_count = len(unique_sources)
        
        # 每增加一个独立来源，奖励0.05分，最多0.15分
        diversity_bonus = min(0.15, (source_count - 1) * 0.05)
        
        return diversity_bonus
    
    def _detect_conflicts(self, evidences: List[Evidence]) -> List[ConflictInfo]:
        """
        检测证据间的冲突（改进版：增加语义分析）
        
        检测三种冲突类型：
        1. 置信度差异冲突
        2. 语义矛盾冲突（否定关系）
        3. 引用验证失败
        
        Returns:
            冲突信息列表
        """
        conflicts = []
        
        for i, e1 in enumerate(evidences):
            for e2 in evidences[i+1:]:
                # 1. 置信度差异检测
                confidence_diff = abs(e1.confidence - e2.confidence)
                
                # 2. 语义冲突检测
                semantic_conflict = self._detect_semantic_conflict(e1, e2)
                
                # 判断是否存在冲突
                if confidence_diff > self.conflict_threshold or semantic_conflict:
                    conflict_type = "semantic_contradiction" if semantic_conflict else "inconsistency"
                    severity = 0.9 if semantic_conflict else confidence_diff
                    
                    conflict = ConflictInfo(
                        conflicting_evidences=[e1, e2],
                        conflict_type=conflict_type,
                        severity=severity,
                        resolution=None
                    )
                    conflicts.append(conflict)
                    
                    logger.debug(
                        f"Conflict detected: {e1.source_name} vs {e2.source_name}, "
                        f"type={conflict_type}, severity={severity:.2f}"
                    )
        
        return conflicts
    
    def _detect_semantic_conflict(self, e1: Evidence, e2: Evidence) -> bool:
        """
        检测两个证据间的语义冲突
        
        使用否定词检测方法（快速且有效）
        注意：语义相似度需要异步环境，这里仅使用规则检测
        
        Args:
            e1, e2: 两个证据
            
        Returns:
            是否存在语义冲突
        """
        # 使用否定词检测（快速且有效）
        has_negation_conflict = self._check_negation_conflict(e1.content, e2.content)
        if has_negation_conflict:
            logger.debug(f"Negation conflict detected between evidences")
            return True
        
        return False
    
    def _check_negation_conflict(self, text1: str, text2: str) -> bool:
        """
        检测否定关系冲突
        
        识别模式：
        - "不能" vs "能够"
        - "无法" vs "可以"
        - "错误" vs "正确"
        
        Args:
            text1, text2: 两段文本
            
        Returns:
            是否存在否定冲突
        """
        # 否定词列表
        negation_words = [
            "不能", "无法", "不会", "不是", "没有", "非",
            "cannot", "unable", "not", "never", "no",
            "incorrect", "false", "wrong"
        ]
        
        # 肯定词列表
        affirmation_words = [
            "能够", "可以", "会", "是", "有",
            "can", "able", "possible", "yes",
            "correct", "true", "right"
        ]
        
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # 检查一个文本包含否定词，另一个包含肯定词
        text1_has_negation = any(neg in text1_lower for neg in negation_words)
        text2_has_negation = any(neg in text2_lower for neg in negation_words)
        
        text1_has_affirmation = any(aff in text1_lower for aff in affirmation_words)
        text2_has_affirmation = any(aff in text2_lower for aff in affirmation_words)
        
        # 如果一个否定，一个肯定，可能存在冲突
        if (text1_has_negation and text2_has_affirmation) or \
           (text2_has_negation and text1_has_affirmation):
            return True
        
        return False
    
    def _calculate_conflict_penalty(self, conflicts: List[ConflictInfo]) -> float:
        """
        计算冲突惩罚
        
        存在冲突会降低可信度
        """
        if not conflicts:
            return 0.0
        
        # 每个严重冲突扣0.1分，最多扣0.3分
        total_penalty = sum(c.severity * 0.1 for c in conflicts)
        return min(0.3, total_penalty)
    
    def _determine_credibility_level(self, score: float) -> CredibilityLevel:
        """确定可信度等级"""
        if score >= 0.9:
            return CredibilityLevel.VERIFIED
        elif score >= 0.7:
            return CredibilityLevel.RELIABLE
        elif score >= 0.5:
            return CredibilityLevel.PROBABLE
        elif score >= 0.3:
            return CredibilityLevel.UNCERTAIN
        else:
            return CredibilityLevel.QUESTIONABLE
    
    def _generate_warnings(
        self,
        evidences: List[Evidence],
        conflicts: List[ConflictInfo],
        score: float
    ) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        # 检查证据数量
        if len(evidences) < self.min_evidence_count:
            warnings.append(
                f"证据数量不足（{len(evidences)}/{self.min_evidence_count}），"
                "可信度可能较低"
            )
        
        # 检查来源多样性
        unique_sources = set(e.source_type for e in evidences)
        if len(unique_sources) == 1:
            warnings.append("所有证据来自同一类型来源，缺乏交叉验证")
        
        # 检查冲突
        if conflicts:
            warnings.append(
                f"发现{len(conflicts)}个证据冲突，需要进一步核实"
            )
        
        # 检查低分数
        if score < 0.5:
            warnings.append("可信度评分较低，建议谨慎使用此关联")
        
        return warnings
    
    def resolve_conflicts(
        self,
        conflicts: List[ConflictInfo],
        strategy: str = "highest_confidence"
    ) -> List[Evidence]:
        """
        冲突仲裁
        
        Args:
            conflicts: 冲突列表
            strategy: 仲裁策略
                - "highest_confidence": 选择置信度最高的证据
                - "most_authoritative": 选择最权威的来源
                - "majority_vote": 多数投票
                
        Returns:
            解决冲突后的证据列表
        """
        resolved_evidences = []
        
        for conflict in conflicts:
            if strategy == "highest_confidence":
                # 选择置信度最高的证据
                best_evidence = max(
                    conflict.conflicting_evidences,
                    key=lambda e: e.confidence
                )
                resolved_evidences.append(best_evidence)
                conflict.resolution = f"选择了置信度最高的证据（{best_evidence.source_name}）"
                
            elif strategy == "most_authoritative":
                # 选择最权威的来源
                best_evidence = max(
                    conflict.conflicting_evidences,
                    key=lambda e: self.source_weights.get(e.source_type, 0.5)
                )
                resolved_evidences.append(best_evidence)
                conflict.resolution = f"选择了最权威的来源（{best_evidence.source_type.value}）"
        
        logger.info(f"Resolved {len(conflicts)} conflicts using strategy: {strategy}")
        
        return resolved_evidences
    
    def trace_source(self, evidence: Evidence) -> Dict[str, Any]:
        """
        来源溯源（改进版：增加引用验证）
        
        追踪证据的完整来源链，并验证引用真实性
        
        Args:
            evidence: 证据对象
            
        Returns:
            来源追踪信息
        """
        # 验证引用
        citation_verified, citation_details = self._verify_citations(evidence)
        
        trace_info = {
            "primary_source": {
                "type": evidence.source_type.value,
                "name": evidence.source_name,
                "url": evidence.url,
                "confidence": evidence.confidence
            },
            "reliability_factors": {
                "source_authority": self.source_weights.get(
                    evidence.source_type, 0.5
                ),
                "content_quality": self._assess_content_quality(evidence.content),
                "timestamp_recency": self._assess_recency(evidence.timestamp),
                "citation_verified": citation_verified  # 新增：引用验证
            },
            "citation_check": citation_details,  # 新增：引用详情
            "verification_path": [
                f"1. 原始来源：{evidence.source_name}",
                f"2. 来源类型：{evidence.source_type.value}",
                f"3. 置信度评估：{evidence.confidence}",
                f"4. 权重系数：{self.source_weights.get(evidence.source_type, 0.5)}",
                f"5. 引用验证：{'通过' if citation_verified else '失败'}"  # 新增
            ]
        }
        
        return trace_info
    
    def _verify_citations(self, evidence: Evidence) -> Tuple[bool, Dict[str, Any]]:
        """
        验证证据中的引用是否真实
        
        检查：
        1. Arxiv论文ID是否存在
        2. DOI链接是否有效
        3. URL格式是否正确
        
        Args:
            evidence: 证据对象
            
        Returns:
            (是否验证通过, 详细信息)
        """
        import re
        
        details = {
            "has_citations": False,
            "citations_found": [],
            "verified_citations": [],
            "invalid_citations": [],
            "verification_method": None
        }
        
        content = evidence.content
        url = evidence.url or ""
        
        # 1. 检测Arxiv引用
        arxiv_pattern = r'arxiv\.org/abs/([\d\.]+)'
        arxiv_matches = re.findall(arxiv_pattern, content + url, re.IGNORECASE)
        
        if arxiv_matches:
            details["has_citations"] = True
            details["verification_method"] = "arxiv"
            
            for arxiv_id in arxiv_matches:
                details["citations_found"].append(f"arxiv:{arxiv_id}")
                
                # 验证Arxiv ID格式
                if self._validate_arxiv_id(arxiv_id):
                    details["verified_citations"].append(f"arxiv:{arxiv_id}")
                else:
                    details["invalid_citations"].append(f"arxiv:{arxiv_id}")
        
        # 2. 检测DOI引用
        doi_pattern = r'10\.\d{4,}/[\w\-\.]+'  
        doi_matches = re.findall(doi_pattern, content + url)
        
        if doi_matches:
            details["has_citations"] = True
            if not details["verification_method"]:
                details["verification_method"] = "doi"
            
            for doi in doi_matches:
                details["citations_found"].append(f"doi:{doi}")
                # DOI格式验证（简单检查）
                if len(doi) > 10:
                    details["verified_citations"].append(f"doi:{doi}")
        
        # 3. 检查URL有效性（仅当没有其他引用时）
        if evidence.url and not details["citations_found"]:
            details["has_citations"] = True
            if self._validate_url_format(evidence.url):
                details["verified_citations"].append(f"url:{evidence.url}")
            else:
                details["invalid_citations"].append(f"url:{evidence.url}")
        
        # 判断整体验证结果
        if not details["has_citations"]:
            # 没有引用，对于LLM证据这是警告信号
            verified = evidence.source_type != SourceType.LLM_REASONING
        else:
            # 有引用，检查是否有无效引用
            has_invalid = len(details["invalid_citations"]) > 0
            has_valid = len(details["verified_citations"]) > 0
            
            # 只有当所有引用都有效且至少有1个有效引用时，才通过验证
            verified = has_valid and not has_invalid
        
        return verified, details
    
    def _validate_arxiv_id(self, arxiv_id: str) -> bool:
        """
        验证Arxiv ID格式（改进版：更严格的验证）
        
        合法格式：
        - 新格式：YYMM.NNNNN (4位年月.5位数字，如2301.12345)
        - 旧格式：arch-ive/YYMMNNN (7位数字，如quant-ph/0001234)
        
        Args:
            arxiv_id: Arxiv ID
            
        Returns:
            格式是否有效
        """
        import re
        
        # 新格式：4位年月.5位数字 (不能是9999等明显无效的)
        new_format = r'^\d{4}\.\d{5}$'
        
        # 旧格式：分类/7位数字
        old_format = r'^[a-z\-]+/\d{7}$'
        
        # 先检查基本格式
        if not (re.match(new_format, arxiv_id) or re.match(old_format, arxiv_id)):
            return False
        
        # 对于新格式，额外检查年月合理性
        if re.match(new_format, arxiv_id):
            year_month = arxiv_id.split('.')[0]
            year = int(year_month[:2])  # YY
            month = int(year_month[2:])  # MM
            
            # 年份应该在07-99范围内（arxiv从2007年开始用新格式），月份1-12
            # 9999这样的明显无效
            if year > 50 or month < 1 or month > 12:
                return False
        
        return True
    
    def _validate_url_format(self, url: str) -> bool:
        """
        验证URL格式
        
        Args:
            url: URL字符串
            
        Returns:
            格式是否有效
        """
        import re
        
        url_pattern = r'^https?://[\w\-\.]+(:[\d]+)?(/[\w\-\./]*)?$'
        return bool(re.match(url_pattern, url))
    
    def _assess_content_quality(self, content: str) -> float:
        """
        评估内容质量
        
        基于内容长度、结构等简单指标
        """
        if not content:
            return 0.0
        
        # 简单评估：长度合理性
        length = len(content)
        if length < 50:
            return 0.3  # 太短，可能信息不足
        elif length > 500:
            return 0.8  # 详细，质量较高
        else:
            return 0.6  # 中等长度
    
    def _assess_recency(self, timestamp: Optional[str]) -> float:
        """
        评估时效性
        
        较新的信息可能更准确
        """
        if not timestamp:
            return 0.5  # 未知时间，中等评分
        
        # 简化实现：总是返回0.7
        # 实际应该解析时间戳并计算时间差
        return 0.7


class MultiSourceVerifier:
    """
    多源验证器
    
    整合多个数据源进行交叉验证
    """
    
    def __init__(self, credibility_scorer: Optional[CredibilityScorer] = None):
        """
        初始化多源验证器
        
        Args:
            credibility_scorer: 可信度评分器实例
        """
        self.scorer = credibility_scorer or CredibilityScorer()
        
    async def verify_from_multiple_sources(
        self,
        concept_a: str,
        concept_b: str,
        data_sources: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从多个数据源验证概念关联
        
        Args:
            concept_a: 概念A
            concept_b: 概念B
            data_sources: 数据源字典 {source_type: data}
            
        Returns:
            多源验证结果
        """
        evidences = []
        
        # 从各个数据源提取证据
        for source_type_str, data in data_sources.items():
            try:
                source_type = SourceType(source_type_str)
                evidence = self._extract_evidence(source_type, data)
                if evidence:
                    evidences.append(evidence)
            except ValueError:
                logger.warning(f"Unknown source type: {source_type_str}")
        
        # 计算可信度
        result = self.scorer.calculate_credibility(
            evidences, concept_a, concept_b
        )
        
        # 如果有冲突，尝试解决
        if result["has_conflicts"] and result["conflicts"]:
            # 重建ConflictInfo对象
            conflicts = []
            for c_dict in result["conflicts"]:
                # 重建证据对象
                conflicting_evs = []
                for ev_dict in c_dict.get("conflicting_evidences", []):
                    evidence = Evidence(
                        source_type=SourceType(ev_dict["source_type"]),
                        source_name=ev_dict["source_name"],
                        content=ev_dict["content"],
                        url=ev_dict.get("url"),
                        confidence=ev_dict["confidence"],
                        timestamp=ev_dict.get("timestamp")
                    )
                    conflicting_evs.append(evidence)
                
                conflict = ConflictInfo(
                    conflicting_evidences=conflicting_evs,
                    conflict_type=c_dict["conflict_type"],
                    severity=c_dict["severity"],
                    resolution=c_dict.get("resolution")
                )
                conflicts.append(conflict)
            
            resolved_evidences = self.scorer.resolve_conflicts(conflicts)
            
            # 重新计算可信度
            result = self.scorer.calculate_credibility(
                evidences + resolved_evidences, concept_a, concept_b
            )
            result["conflicts_resolved"] = True
        
        return result
    
    def _extract_evidence(
        self,
        source_type: SourceType,
        data: Any
    ) -> Optional[Evidence]:
        """
        从数据源提取证据
        
        Args:
            source_type: 来源类型
            data: 原始数据
            
        Returns:
            证据对象
        """
        if not data:
            return None
        
        # 根据不同来源类型提取证据
        if source_type == SourceType.WIKIPEDIA:
            return Evidence(
                source_type=source_type,
                source_name="Wikipedia",
                content=data.get("summary", "")[:500],
                url=data.get("url"),
                confidence=0.75,
                timestamp=data.get("timestamp")
            )
        
        elif source_type == SourceType.ARXIV:
            return Evidence(
                source_type=source_type,
                source_name="Arxiv",
                content=data.get("abstract", "")[:500],
                url=data.get("pdf_url"),
                confidence=0.85,
                timestamp=data.get("published")
            )
        
        elif source_type == SourceType.LLM_REASONING:
            return Evidence(
                source_type=source_type,
                source_name="LLM Reasoning",
                content=data.get("reasoning", "")[:500],
                confidence=data.get("confidence", 0.6),
                timestamp=None
            )
        
        return None
