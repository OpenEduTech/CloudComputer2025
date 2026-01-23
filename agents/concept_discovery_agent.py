"""概念关联挖掘Agent"""

import logging
from typing import List, Dict, Any, Optional
from prompts.discovery_prompts import DiscoveryPrompt
from shared.constants import Discipline, AgentConfig
from shared.utils import generate_node_id
from agents.llm_client import get_llm_client
from agents.utils import validate_json_output, extract_concepts_from_response

logger = logging.getLogger(__name__)


class ConceptDiscoveryAgent:
    """概念关联挖掘Agent"""
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.prompt_generator = DiscoveryPrompt()
    
    async def discover_concepts(
        self,
        concept: str,
        disciplines: Optional[List[str]] = None,
        depth: int = AgentConfig.DEFAULT_DEPTH,
        max_concepts: int = AgentConfig.DEFAULT_MAX_CONCEPTS
    ) -> Dict[str, Any]:
        """
        发现跨学科相关概念
        
        Args:
            concept: 核心概念
            disciplines: 目标学科列表
            depth: 挖掘深度
            max_concepts: 最大概念数
            
        Returns:
            发现的概念和关系
        """
        logger.info(f"Discovering concepts for: {concept}")
        
        # 使用默认学科列表
        if not disciplines:
            disciplines = Discipline.ALL
        
        # 允许非标准学科（如"信息论"等细分领域），由LLM处理
        # 只验证非空即可
        if not disciplines or all(not d.strip() for d in disciplines):
            raise ValueError("Disciplines cannot be empty")
        
        try:
            # 生成Prompt
            prompt = self.prompt_generator.get_discovery_prompt(
                concept=concept,
                disciplines=disciplines,
                depth=depth
            )
            
            # 调用LLM
            response = await self.llm_client.call_json(
                prompt=prompt,
                system_role="你是一个跨学科知识专家，擅长发现不同领域之间的深层联系。"
            )
            
            # 提取概念列表
            concepts = extract_concepts_from_response(response)
            
            if not concepts:
                logger.warning(f"No concepts found for: {concept}")
                return {
                    "source_concept": concept,
                    "related_concepts": [],
                    "count": 0
                }
            
            # 限制数量
            if len(concepts) > max_concepts:
                concepts = sorted(
                    concepts,
                    key=lambda c: c.get('strength', 0.0),
                    reverse=True
                )[:max_concepts]
            
            logger.info(f"Found {len(concepts)} related concepts")
            
            return {
                "source_concept": concept,
                "related_concepts": concepts,
                "count": len(concepts)
            }
            
        except Exception as e:
            logger.error(f"Concept discovery failed: {str(e)}")
            raise
    
    async def expand_node(
        self,
        parent_concept: str,
        parent_discipline: str,
        target_disciplines: Optional[List[str]] = None,
        max_new_nodes: int = 10
    ) -> Dict[str, Any]:
        """
        扩展节点（增量挖掘）
        
        Args:
            parent_concept: 父节点概念
            parent_discipline: 父节点学科
            target_disciplines: 目标扩展学科
            max_new_nodes: 最多新增节点数
            
        Returns:
            新增的概念和关系
        """
        logger.info(f"Expanding node: {parent_concept} ({parent_discipline})")
        
        # 使用默认学科列表
        if not target_disciplines:
            target_disciplines = Discipline.ALL
        
        try:
            # 生成扩展Prompt
            prompt = self.prompt_generator.get_expansion_prompt(
                parent_concept=parent_concept,
                parent_discipline=parent_discipline,
                target_disciplines=target_disciplines
            )
            
            # 调用LLM
            response = await self.llm_client.call_json(
                prompt=prompt,
                system_role="你是一个跨学科知识专家。"
            )
            
            # 提取概念列表
            concepts = extract_concepts_from_response(response)
            
            # 限制数量
            if len(concepts) > max_new_nodes:
                concepts = sorted(
                    concepts,
                    key=lambda c: c.get('strength', 0.0),
                    reverse=True
                )[:max_new_nodes]
            
            logger.info(f"Expanded {len(concepts)} new concepts")
            
            return {
                "parent_concept": parent_concept,
                "parent_discipline": parent_discipline,
                "new_concepts": concepts,
                "count": len(concepts)
            }
            
        except Exception as e:
            logger.error(f"Node expansion failed: {str(e)}")
            raise
    
    async def search_by_discipline(
        self,
        concept: str,
        discipline: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        在特定学科中搜索相关概念
        
        Args:
            concept: 核心概念
            discipline: 目标学科
            max_results: 最大结果数
            
        Returns:
            概念列表
        """
        logger.info(f"Searching in {discipline} for: {concept}")
        
        if discipline not in Discipline.ALL:
            raise ValueError(f"Invalid discipline: {discipline}")
        
        # 使用单学科挖掘
        result = await self.discover_concepts(
            concept=concept,
            disciplines=[discipline],
            depth=1,
            max_concepts=max_results
        )
        
        return result.get('related_concepts', [])
