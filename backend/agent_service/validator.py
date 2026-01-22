"""
校验层 (Check Layer)
防止LLM幻觉，确保知识图谱的准确性
"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from .llm_client import LLMClient
from .prompts import (
    RELATION_VALIDATION_PROMPT,
    REVERSE_VALIDATION_PROMPT,
    SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)


class ValidationLayer:
    """校验层类"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.consistency_threshold = 0.7  # 一致性阈值
        self.confidence_threshold = 0.6   # 置信度阈值
    
    async def validate_relation(
        self,
        source_concept: str,
        source_domain: str,
        target_concept: str,
        target_domain: str,
        relation_type: str,
        explanation: str
    ) -> Dict[str, Any]:
        """
        验证单个关系的有效性
        
        Args:
            source_concept: 源概念
            source_domain: 源学科
            target_concept: 目标概念
            target_domain: 目标学科
            relation_type: 关系类型
            explanation: 关系说明
            
        Returns:
            验证结果字典
        """
        logger.info(f"Validating relation: {source_concept} -> {target_concept}")
        
        # 方法1: 直接验证
        direct_validation = await self._direct_validation(
            source_concept, source_domain,
            target_concept, target_domain,
            relation_type, explanation
        )
        
        # 方法2: 反向验证
        reverse_validation = await self._reverse_validation(
            source_concept, source_domain,
            target_concept, target_domain,
            relation_type
        )
        
        # 综合判断
        is_valid = (
            direct_validation.get("valid", False) and
            direct_validation.get("confidence", 0) >= self.confidence_threshold and
            reverse_validation.get("reverse_valid", False) and
            reverse_validation.get("confidence", 0) >= self.confidence_threshold
        )
        
        final_confidence = (
            direct_validation.get("confidence", 0) * 0.6 +
            reverse_validation.get("confidence", 0) * 0.4
        )
        
        result = {
            "valid": is_valid,
            "confidence": final_confidence,
            "direct_validation": direct_validation,
            "reverse_validation": reverse_validation,
            "suggested_strength": direct_validation.get("suggested_strength", 5)
        }
        
        logger.info(f"Validation result: valid={is_valid}, confidence={final_confidence:.2f}")
        
        return result
    
    async def validate_relation_fast(
        self,
        source_concept: str,
        source_domain: str,
        target_concept: str,
        target_domain: str,
        relation_type: str,
        explanation: str
    ) -> Dict[str, Any]:
        """
        快速验证单个关系（只做直接验证）
        
        Args:
            source_concept: 源概念
            source_domain: 源学科
            target_concept: 目标概念
            target_domain: 目标学科
            relation_type: 关系类型
            explanation: 关系说明
            
        Returns:
            验证结果字典
        """
        logger.info(f"Fast validating relation: {source_concept} -> {target_concept}")
        
        # 只做直接验证
        direct_validation = await self._direct_validation(
            source_concept, source_domain,
            target_concept, target_domain,
            relation_type, explanation
        )
        
        # 降低阈值以提高通过率
        is_valid = (
            direct_validation.get("valid", False) and
            direct_validation.get("confidence", 0) >= (self.confidence_threshold * 0.8)
        )
        
        result = {
            "valid": is_valid,
            "confidence": direct_validation.get("confidence", 0),
            "direct_validation": direct_validation,
            "suggested_strength": direct_validation.get("suggested_strength", 5)
        }
        
        logger.info(f"Fast validation result: valid={is_valid}, confidence={result['confidence']:.2f}")
        
        return result
    
    async def _direct_validation(
        self,
        source_concept: str,
        source_domain: str,
        target_concept: str,
        target_domain: str,
        relation_type: str,
        explanation: str
    ) -> Dict[str, Any]:
        """直接验证"""
        try:
            prompt = RELATION_VALIDATION_PROMPT.format(
                source_concept=source_concept,
                source_domain=source_domain,
                target_concept=target_concept,
                target_domain=target_domain,
                relation_type=relation_type,
                explanation=explanation
            )
            
            result = await self.llm_client.call_llm_json(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3  # 低温度以获得更确定的结果
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Direct validation failed: {str(e)}")
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": f"Validation error: {str(e)}",
                "suggested_strength": 0
            }
    
    async def _reverse_validation(
        self,
        source_concept: str,
        source_domain: str,
        target_concept: str,
        target_domain: str,
        relation_type: str
    ) -> Dict[str, Any]:
        """反向验证"""
        try:
            prompt = REVERSE_VALIDATION_PROMPT.format(
                source_concept=source_concept,
                source_domain=source_domain,
                target_concept=target_concept,
                target_domain=target_domain,
                relation_type=relation_type
            )
            
            result = await self.llm_client.call_llm_json(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Reverse validation failed: {str(e)}")
            return {
                "reverse_valid": False,
                "confidence": 0.0,
                "reason": f"Validation error: {str(e)}"
            }
    
    async def validate_relations_batch(
        self,
        relations: List[Dict[str, Any]],
        fast_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        批量验证关系（并行优化版本）
        
        Args:
            relations: 关系列表
            fast_mode: 快速模式（只做直接验证，跳过反向验证）
            
        Returns:
            验证后的关系列表（只包含有效关系）
        """
        logger.info(f"Validating {len(relations)} relations (fast_mode={fast_mode})")
        
        # 并行验证所有关系
        validation_tasks = []
        for relation in relations:
            if fast_mode:
                task = self.validate_relation_fast(
                    source_concept=relation.get("source_concept", ""),
                    source_domain=relation.get("source_domain", ""),
                    target_concept=relation.get("target_concept", ""),
                    target_domain=relation.get("target_domain", ""),
                    relation_type=relation.get("relation_type", ""),
                    explanation=relation.get("explanation", "")
                )
            else:
                task = self.validate_relation(
                    source_concept=relation.get("source_concept", ""),
                    source_domain=relation.get("source_domain", ""),
                    target_concept=relation.get("target_concept", ""),
                    target_domain=relation.get("target_domain", ""),
                    relation_type=relation.get("relation_type", ""),
                    explanation=relation.get("explanation", "")
                )
            validation_tasks.append(task)
        
        # 并行执行所有验证任务
        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # 处理验证结果
        validated_relations = []
        for relation, validation_result in zip(relations, validation_results):
            try:
                # 如果验证出错，跳过该关系
                if isinstance(validation_result, Exception):
                    logger.error(f"Error validating relation: {str(validation_result)}")
                    continue
                
                if validation_result["valid"]:
                    # 更新关系强度
                    relation["relation_strength"] = validation_result["suggested_strength"]
                    relation["confidence"] = validation_result["confidence"]
                    relation["validation_details"] = validation_result
                    validated_relations.append(relation)
                else:
                    logger.info(
                        f"Relation rejected: {relation['source_concept']} -> "
                        f"{relation['target_concept']} (confidence: {validation_result['confidence']:.2f})"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing validation result: {str(e)}")
                continue
        
        logger.info(f"Validated {len(validated_relations)} out of {len(relations)} relations")
        
        return validated_relations
    
    async def check_consistency(
        self,
        prompt: str,
        n: int = 3
    ) -> Dict[str, Any]:
        """
        一致性检查：多次采样验证结果一致性
        
        Args:
            prompt: 提示词
            n: 采样次数
            
        Returns:
            一致性检查结果
        """
        try:
            responses = await self.llm_client.call_llm_multiple(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                n=n,
                temperature=0.7
            )
            
            # 尝试解析JSON并比较
            parsed_responses = []
            for resp in responses:
                try:
                    resp = resp.strip()
                    if resp.startswith("```json"):
                        resp = resp[7:]
                    if resp.startswith("```"):
                        resp = resp[3:]
                    if resp.endswith("```"):
                        resp = resp[:-3]
                    resp = resp.strip()
                    
                    parsed = json.loads(resp)
                    parsed_responses.append(parsed)
                except:
                    continue
            
            if len(parsed_responses) < 2:
                return {
                    "consistent": False,
                    "consistency_score": 0.0,
                    "reason": "Not enough valid responses"
                }
            
            # 简单的一致性检查：比较关键字段
            consistency_score = self._calculate_consistency(parsed_responses)
            
            return {
                "consistent": consistency_score >= self.consistency_threshold,
                "consistency_score": consistency_score,
                "responses": parsed_responses
            }
            
        except Exception as e:
            logger.error(f"Consistency check failed: {str(e)}")
            return {
                "consistent": False,
                "consistency_score": 0.0,
                "reason": str(e)
            }
    
    def _calculate_consistency(self, responses: List[Dict[str, Any]]) -> float:
        """计算响应的一致性分数"""
        if len(responses) < 2:
            return 0.0
        
        # 简单实现：比较第一个响应与其他响应的相似度
        base = responses[0]
        similarities = []
        
        for resp in responses[1:]:
            similarity = self._compare_responses(base, resp)
            similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _compare_responses(self, resp1: Dict[str, Any], resp2: Dict[str, Any]) -> float:
        """比较两个响应的相似度"""
        # 简单实现：比较关键字段
        score = 0.0
        total = 0
        
        for key in resp1.keys():
            if key in resp2:
                total += 1
                if resp1[key] == resp2[key]:
                    score += 1
                elif isinstance(resp1[key], (int, float)) and isinstance(resp2[key], (int, float)):
                    # 数值类型：计算相对差异
                    diff = abs(resp1[key] - resp2[key]) / max(abs(resp1[key]), abs(resp2[key]), 1)
                    score += max(0, 1 - diff)
        
        return score / total if total > 0 else 0.0
