"""
Agent Service主逻辑
协调LLM调用、校验和图谱构建
"""
import logging
from typing import Dict, Any, List, Optional
from .llm_client import LLMClient
from .validator import ValidationLayer
from .prompts import (
    CONCEPT_IDENTIFICATION_PROMPT,
    CROSS_DOMAIN_MINING_PROMPT,
    CONCEPT_EXPANSION_PROMPT,
    SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)


class AgentService:
    """智能体服务类"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.validator = ValidationLayer(self.llm_client)
        logger.info("Agent Service initialized")
    
    async def generate_knowledge_graph(
        self,
        concept: str,
        enable_validation: bool = True,
        fast_mode: bool = True
    ) -> Dict[str, Any]:
        """
        生成知识图谱
        
        Args:
            concept: 核心概念
            enable_validation: 是否启用校验层
            fast_mode: 快速模式（只做直接验证，跳过反向验证）
            
        Returns:
            知识图谱数据
        """
        logger.info(f"Generating knowledge graph for concept: {concept} (fast_mode={fast_mode})")
        
        try:
            # 阶段1: 概念识别
            concept_info = await self._identify_concept(concept)
            logger.info(f"Concept identified: {concept_info}")
            
            # 阶段2: 跨学科关联挖掘
            relations = await self._mine_cross_domain_relations(concept_info)
            logger.info(f"Mined {len(relations)} relations")
            
            # 阶段3: 校验层验证（可选）
            if enable_validation:
                relations = await self.validator.validate_relations_batch(
                    relations, 
                    fast_mode=fast_mode
                )
                logger.info(f"After validation: {len(relations)} valid relations")
            
            # 阶段4: 构建图谱数据结构
            graph_data = self._build_graph_structure(concept_info, relations)
            
            logger.info(f"Knowledge graph generated successfully")
            
            return {
                "success": True,
                "concept": concept,
                "concept_info": concept_info,
                "graph": graph_data,
                "stats": {
                    "total_nodes": len(graph_data["nodes"]),
                    "total_edges": len(graph_data["edges"]),
                    "domains_covered": len(set(n["domain"] for n in graph_data["nodes"]))
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate knowledge graph: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "concept": concept
            }
    
    async def _identify_concept(self, concept: str) -> Dict[str, Any]:
        """识别概念的基本信息"""
        prompt = CONCEPT_IDENTIFICATION_PROMPT.format(concept=concept)
        
        result = await self.llm_client.call_llm_json(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3
        )
        
        return result
    
    async def _mine_cross_domain_relations(
        self,
        concept_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """挖掘跨学科关联"""
        prompt = CROSS_DOMAIN_MINING_PROMPT.format(
            concept=concept_info.get("concept", ""),
            primary_domain=concept_info.get("primary_domain", ""),
            definition=concept_info.get("definition", "")
        )
        
        result = await self.llm_client.call_llm_json(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7
        )
        
        relations = result.get("relations", [])
        
        # 添加源学科信息
        for relation in relations:
            relation["source_domain"] = concept_info.get("primary_domain", "Unknown")
        
        return relations
    
    async def expand_concept(
        self,
        concept: str,
        domain: str,
        enable_validation: bool = True,
        fast_mode: bool = True
    ) -> Dict[str, Any]:
        """
        扩展单个概念
        
        Args:
            concept: 要扩展的概念
            domain: 概念所属学科
            enable_validation: 是否启用校验
            fast_mode: 快速模式
            
        Returns:
            扩展结果
        """
        logger.info(f"Expanding concept: {concept} ({domain}) (fast_mode={fast_mode})")
        
        try:
            prompt = CONCEPT_EXPANSION_PROMPT.format(
                concept=concept,
                domain=domain
            )
            
            result = await self.llm_client.call_llm_json(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.7
            )
            
            expansions = result.get("expansions", [])
            
            # 转换为关系格式
            relations = []
            for exp in expansions:
                relations.append({
                    "source_concept": concept,
                    "source_domain": domain,
                    "target_concept": exp.get("concept", ""),
                    "target_domain": exp.get("domain", ""),
                    "relation_type": exp.get("relation_type", ""),
                    "relation_strength": exp.get("relation_strength", 5),
                    "explanation": exp.get("explanation", "")
                })
            
            # 校验
            if enable_validation:
                relations = await self.validator.validate_relations_batch(
                    relations,
                    fast_mode=fast_mode
                )
            
            return {
                "success": True,
                "concept": concept,
                "domain": domain,
                "expansions": relations,
                "count": len(relations)
            }
            
        except Exception as e:
            logger.error(f"Failed to expand concept: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "concept": concept
            }
    
    def _build_graph_structure(
        self,
        concept_info: Dict[str, Any],
        relations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建图谱数据结构
        
        Returns:
            {
                "nodes": [...],
                "edges": [...]
            }
        """
        nodes = []
        edges = []
        node_ids = set()
        
        # 添加中心节点
        center_node = {
            "id": concept_info.get("concept", ""),
            "label": concept_info.get("concept", ""),
            "domain": concept_info.get("primary_domain", ""),
            "definition": concept_info.get("definition", ""),
            "keywords": concept_info.get("keywords", []),
            "type": "center"
        }
        nodes.append(center_node)
        node_ids.add(center_node["id"])
        
        # 添加关联节点和边
        for idx, relation in enumerate(relations):
            target_id = relation.get("target_concept", "")
            
            # 添加目标节点（如果不存在）
            if target_id and target_id not in node_ids:
                target_node = {
                    "id": target_id,
                    "label": target_id,
                    "domain": relation.get("target_domain", ""),
                    "type": "related"
                }
                nodes.append(target_node)
                node_ids.add(target_id)
            
            # 添加边
            if target_id:
                edge = {
                    "id": f"edge_{idx}",
                    "source": relation.get("source_concept", ""),
                    "target": target_id,
                    "relation_type": relation.get("relation_type", ""),
                    "strength": relation.get("relation_strength", 5),
                    "explanation": relation.get("explanation", ""),
                    "confidence": relation.get("confidence", 1.0)
                }
                edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges
        }
