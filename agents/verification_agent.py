"""知识校验Agent - 整合多源验证和可信度评分"""

import logging
from typing import List, Dict, Any, Optional
from prompts.verification_prompts import VerificationPrompt
from shared.constants import AgentConfig
from agents.llm_client import get_llm_client
from agents.utils import validate_json_output
from algorithms.credibility_scorer import (
    CredibilityScorer, 
    MultiSourceVerifier,
    Evidence,
    SourceType
)
from algorithms.data_crawler import DataCrawler

logger = logging.getLogger(__name__)


class VerificationAgent:
    """
    知识校验Agent
    
    核心功能：
    1. 多源验证：整合Wikipedia、Arxiv、LLM推理
    2. 可信度评分：基于证据质量计算分数
    3. 冲突检测：识别并解决证据矛盾
    4. 来源溯源：追踪信息来源链
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.prompt_generator = VerificationPrompt()
        self.credibility_threshold = AgentConfig.CREDIBILITY_THRESHOLD
        
        # 新增：可信度评分器和多源验证器（改进版）
        self.credibility_scorer = CredibilityScorer(
            min_evidence_count=2,
            wikipedia_weight=0.7,
            arxiv_weight=0.9,
            llm_weight=0.3,  # 降低到0.3，减少幻觉风险
            conflict_threshold=0.6,
            semantic_conflict_threshold=0.75  # 语义冲突阈值
        )
        self.multi_source_verifier = MultiSourceVerifier(self.credibility_scorer)
        self.data_crawler = DataCrawler()
        
        logger.info("VerificationAgent initialized with enhanced multi-source verification (LLM weight=0.3)")
    
    async def verify_relation(
        self,
        concept_a: str,
        concept_b: str,
        claimed_relation: str,
        strength: float,
        enable_multi_source: bool = True
    ) -> Dict[str, Any]:
        """
        验证概念关联的准确性（支持多源验证）
        
        Args:
            concept_a: 概念A
            concept_b: 概念B
            claimed_relation: 声称的关联
            strength: 声称的关联强度
            enable_multi_source: 是否启用多源验证
            
        Returns:
            验证结果
        """
        logger.info(f"Verifying relation: {concept_a} -> {concept_b}")
        
        try:
            # 如果启用多源验证，收集多个来源的证据
            if enable_multi_source:
                return await self._verify_with_multi_source(
                    concept_a, concept_b, claimed_relation, strength
                )
            
            # 否则使用基础LLM验证
            return await self._verify_with_llm_only(
                concept_a, concept_b, claimed_relation, strength
            )
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            raise
    
    async def _verify_with_multi_source(
        self,
        concept_a: str,
        concept_b: str,
        claimed_relation: str,
        strength: float
    ) -> Dict[str, Any]:
        """
        使用多源验证（Wikipedia + Arxiv + LLM）
        
        Returns:
            包含可信度评分和证据的验证结果
        """
        # 1. 收集来自不同源的证据
        data_sources = {}
        
        # 1.1 Wikipedia证据
        try:
            wiki_data = await self.data_crawler.search_wikipedia(
                f"{concept_a} {concept_b}"
            )
            if wiki_data:
                data_sources["wikipedia"] = wiki_data
        except Exception as e:
            logger.warning(f"Wikipedia search failed: {str(e)}")
        
        # 1.2 Arxiv证据
        try:
            arxiv_results = await self.data_crawler.search_arxiv(
                f"{concept_a} {concept_b}",
                max_results=3
            )
            if arxiv_results:
                data_sources["arxiv"] = arxiv_results[0] if arxiv_results else None
        except Exception as e:
            logger.warning(f"Arxiv search failed: {str(e)}")
        
        # 1.3 LLM推理证据
        try:
            llm_result = await self._get_llm_reasoning(
                concept_a, concept_b, claimed_relation, strength
            )
            data_sources["llm_reasoning"] = llm_result
        except Exception as e:
            logger.warning(f"LLM reasoning failed: {str(e)}")
        
        # 2. 使用多源验证器计算可信度
        verification_result = await self.multi_source_verifier.verify_from_multiple_sources(
            concept_a, concept_b, data_sources
        )
        
        # 3. 构建返回结果
        result = {
            "concept_a": concept_a,
            "concept_b": concept_b,
            "credibility_score": verification_result["credibility_score"],
            "credibility_level": verification_result["credibility_level"],
            "is_valid": verification_result["credibility_score"] >= self.credibility_threshold,
            "evidence": verification_result["evidences"],
            "evidence_count": verification_result["evidence_count"],
            "source_diversity": verification_result["source_diversity"],
            "has_conflicts": verification_result["has_conflicts"],
            "conflicts": verification_result.get("conflicts", []),
            "logical_reasoning": claimed_relation,
            "warnings": verification_result["warnings"]
        }
        
        logger.info(
            f"Multi-source verification: {concept_a} -> {concept_b}, "
            f"score={result['credibility_score']:.3f}, "
            f"sources={verification_result['evidence_count']}"
        )
        
        return result
    
    async def _verify_with_llm_only(
        self,
        concept_a: str,
        concept_b: str,
        claimed_relation: str,
        strength: float
    ) -> Dict[str, Any]:
        """
        仅使用LLM进行验证（原有逻辑）
        
        Returns:
            验证结果
        """
    async def _verify_with_llm_only(
        self,
        concept_a: str,
        concept_b: str,
        claimed_relation: str,
        strength: float
    ) -> Dict[str, Any]:
        """
        仅使用LLM进行验证（原有逻辑）
        
        Returns:
            验证结果
        """
        # 生成验证Prompt
        prompt = self.prompt_generator.get_verification_prompt(
            concept_a=concept_a,
            concept_b=concept_b,
            claimed_relation=claimed_relation,
            strength=strength
        )
        
        # 调用LLM
        response = await self.llm_client.call_json(
            prompt=prompt,
            system_role="你是一个严谨的知识验证专家，负责核查信息的准确性。"
        )
        
        # 检查响应有效性
        if not response:
            logger.error("LLM returned None response")
            return {
                "concept_a": concept_a,
                "concept_b": concept_b,
                "credibility_score": 0.0,
                "is_valid": False,
                "evidence": [],
                "logical_reasoning": "LLM验证失败",
                "warnings": ["LLM响应为空"]
            }
        
        # 提取验证结果
        credibility_score = response.get('credibility_score', 0.0)
        is_valid = credibility_score >= self.credibility_threshold
        
        result = {
            "concept_a": concept_a,
            "concept_b": concept_b,
            "credibility_score": credibility_score,
            "is_valid": is_valid,
            "evidence": response.get('evidence', []),
            "logical_reasoning": response.get('logical_reasoning', ''),
            "warnings": response.get('warnings', [])
        }
        
        # 如果可信度低，添加警告
        if not is_valid:
            if not result['warnings']:
                result['warnings'] = []
            result['warnings'].append(
                f"可信度 ({credibility_score:.2f}) 低于阈值 ({self.credibility_threshold})"
            )
        
        logger.info(f"Verification result: credibility={credibility_score:.2f}, valid={is_valid}")
        
        return result
    
    async def _get_llm_reasoning(
        self,
        concept_a: str,
        concept_b: str,
        claimed_relation: str,
        strength: float
    ) -> Dict[str, Any]:
        """
        获取LLM推理证据
        
        Returns:
            LLM推理结果
        """
        prompt = self.prompt_generator.get_verification_prompt(
            concept_a=concept_a,
            concept_b=concept_b,
            claimed_relation=claimed_relation,
            strength=strength
        )
        
        response = await self.llm_client.call_json(
            prompt=prompt,
            system_role="你是一个严谨的知识验证专家。"
        )
        
        if response:
            return {
                "reasoning": response.get('logical_reasoning', ''),
                "confidence": response.get('credibility_score', 0.5)
            }
        else:
            return {
                "reasoning": "LLM推理失败",
                "confidence": 0.3
            }
    
    async def batch_verify(
        self,
        relations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量验证概念关联
        
        Args:
            relations: 待验证的关系列表
            
        Returns:
            验证结果列表
        """
        logger.info(f"Batch verifying {len(relations)} relations")
        
        try:
            # 生成批量验证Prompt
            prompt = self.prompt_generator.get_batch_verification_prompt(relations)
            
            # 调用LLM
            response = await self.llm_client.call_json(
                prompt=prompt,
                system_role="你是一个严谨的知识验证专家。"
            )
            
            # 确保响应是列表
            if not isinstance(response, list):
                response = [response]
            
            # 处理验证结果
            results = []
            for item in response:
                credibility_score = item.get('credibility_score', 0.0)
                is_valid = credibility_score >= self.credibility_threshold
                
                results.append({
                    "index": item.get('index', 0),
                    "concept_a": item.get('concept_a', ''),
                    "concept_b": item.get('concept_b', ''),
                    "credibility_score": credibility_score,
                    "is_valid": is_valid,
                    "quick_reasoning": item.get('quick_reasoning', ''),
                    "warnings": item.get('warnings', [])
                })
            
            verified_count = sum(1 for r in results if r['is_valid'])
            logger.info(f"Batch verification complete: {verified_count}/{len(results)} passed")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch verification failed: {str(e)}")
            raise
    
    async def verify_concepts(
        self,
        concepts: List[Dict[str, Any]],
        source_concept: str
    ) -> List[Dict[str, Any]]:
        """
        验证发现的概念列表
        
        Args:
            concepts: 概念列表
            source_concept: 源概念
            
        Returns:
            验证后的概念列表（可信度评分）
        """
        logger.info(f"Verifying {len(concepts)} concepts")
        
        verified_concepts = []
        
        for concept in concepts:
            try:
                concept_name = concept.get('concept_name', '')
                reasoning = concept.get('reasoning', '')
                strength = concept.get('strength', 0.5)
                
                # 验证关联
                verification = await self.verify_relation(
                    concept_a=source_concept,
                    concept_b=concept_name,
                    claimed_relation=reasoning,
                    strength=strength
                )
                
                # 更新可信度
                concept['credibility'] = verification['credibility_score']
                concept['verification'] = {
                    "is_valid": verification['is_valid'],
                    "evidence": verification['evidence'],
                    "warnings": verification['warnings']
                }
                
                # 只保留有效的概念
                if verification['is_valid']:
                    verified_concepts.append(concept)
                else:
                    logger.warning(f"Concept filtered: {concept_name} (credibility={verification['credibility_score']:.2f})")
                
            except Exception as e:
                logger.error(f"Failed to verify concept {concept.get('concept_name')}: {str(e)}")
                continue
        
        logger.info(f"Verification complete: {len(verified_concepts)}/{len(concepts)} passed")
        
        return verified_concepts
    
    async def check_fact(self, statement: str) -> Dict[str, Any]:
        """
        事实核查
        
        Args:
            statement: 待核查的陈述
            
        Returns:
            核查结果
        """
        logger.info(f"Checking fact: {statement[:100]}...")
        
        try:
            prompt = self.prompt_generator.get_fact_check_prompt(statement)
            
            response = await self.llm_client.call_json(
                prompt=prompt,
                system_role="你是一个事实核查专家。"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Fact check failed: {str(e)}")
            raise
