"""图谱构建Agent"""

import logging
from typing import List, Dict, Any, Optional
from prompts.graph_prompts import GraphPrompt
from shared.schemas import ConceptNode, ConceptEdge
from shared.utils import generate_node_id, calculate_avg_credibility
from agents.llm_client import get_llm_client
from agents.utils import validate_json_output, calculate_graph_metrics, merge_nodes, merge_edges

logger = logging.getLogger(__name__)


class GraphBuilderAgent:
    """图谱构建Agent"""
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.prompt_generator = GraphPrompt()
    
    async def build_graph(
        self,
        source_concept: str,
        verified_concepts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建知识图谱
        
        Args:
            source_concept: 源概念
            verified_concepts: 已验证的概念列表
            
        Returns:
            图谱数据（nodes + edges）
        """
        logger.info(f"Building graph for {len(verified_concepts)} concepts")
        
        if not verified_concepts:
            logger.warning("No concepts to build graph")
            return {
                "nodes": [],
                "edges": [],
                "metadata": {
                    "total_nodes": 0,
                    "total_edges": 0,
                    "verified_nodes": 0,
                    "avg_credibility": 0.0
                }
            }
        
        try:
            # 生成图谱构建Prompt
            prompt = self.prompt_generator.get_graph_builder_prompt(verified_concepts)
            
            # 调用LLM
            response = await self.llm_client.call_json(
                prompt=prompt,
                system_role="你是一个图数据结构专家，擅长将知识转换为标准化的图结构。"
            )
            
            # 提取节点和边
            nodes = response.get('nodes', [])
            edges = response.get('edges', [])
            
            # 添加源概念节点（如果不存在）
            source_node_exists = any(
                source_concept in node.get('label', '') 
                for node in nodes
            )
            
            if not source_node_exists and verified_concepts:
                # 从第一个概念推断源概念的学科
                first_discipline = verified_concepts[0].get('discipline', '未知')
                source_node = {
                    "id": generate_node_id(source_concept, first_discipline),
                    "label": source_concept,
                    "discipline": first_discipline,
                    "definition": f"{source_concept}的核心概念",
                    "credibility": 1.0
                }
                nodes.insert(0, source_node)
            
            # 验证节点和边的完整性
            nodes = self._validate_nodes(nodes)
            edges = self._validate_edges(edges, nodes)
            
            # 计算元数据
            metadata = calculate_graph_metrics(nodes, edges)
            
            logger.info(f"Graph built: {len(nodes)} nodes, {len(edges)} edges")
            
            return {
                "nodes": nodes,
                "edges": edges,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Graph building failed: {str(e)}")
            # 降级：手动构建图谱
            return self._build_graph_fallback(source_concept, verified_concepts)
    
    def _validate_nodes(self, nodes: List[Dict]) -> List[Dict]:
        """验证节点数据完整性"""
        valid_nodes = []
        
        for node in nodes:
            # 确保必需字段存在
            if not node.get('id') or not node.get('label'):
                logger.warning(f"Invalid node: {node}")
                continue
            
            # 填充默认值
            node.setdefault('discipline', '未知')
            node.setdefault('definition', node.get('label', ''))
            node.setdefault('credibility', 0.5)
            
            # 确保可信度在有效范围内
            node['credibility'] = max(0.0, min(1.0, node['credibility']))
            
            valid_nodes.append(node)
        
        return valid_nodes
    
    def _validate_edges(self, edges: List[Dict], nodes: List[Dict]) -> List[Dict]:
        """验证边数据完整性"""
        node_ids = {node.get('id') for node in nodes}
        valid_edges = []
        
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            
            # 确保source和target都存在
            if not source or not target:
                logger.warning(f"Invalid edge: {edge}")
                continue
            
            # 确保引用的节点存在
            if source not in node_ids or target not in node_ids:
                logger.warning(f"Edge references non-existent nodes: {source} -> {target}")
                continue
            
            # 填充默认值
            edge.setdefault('relation', 'related_to')
            edge.setdefault('weight', 0.5)
            edge.setdefault('reasoning', f"{source} 与 {target} 相关")
            
            # 确保权重在有效范围内
            edge['weight'] = max(0.0, min(1.0, edge['weight']))
            
            valid_edges.append(edge)
        
        return valid_edges
    
    def _build_graph_fallback(
        self,
        source_concept: str,
        concepts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        降级方案：手动构建图谱
        
        Args:
            source_concept: 源概念
            concepts: 概念列表
            
        Returns:
            图谱数据
        """
        logger.info("Using fallback graph builder")
        
        nodes = []
        edges = []
        
        # 创建源节点
        source_discipline = concepts[0].get('discipline', '未知') if concepts else '未知'
        source_node_id = generate_node_id(source_concept, source_discipline)
        
        nodes.append({
            "id": source_node_id,
            "label": source_concept,
            "discipline": source_discipline,
            "definition": f"{source_concept}的核心概念",
            "credibility": 1.0
        })
        
        # 创建其他节点和边
        for concept in concepts:
            concept_name = concept.get('concept_name', 'Unknown')
            discipline = concept.get('discipline', '未知')
            definition = concept.get('definition', concept_name)
            credibility = concept.get('credibility', 0.5)
            strength = concept.get('strength', 0.5)
            
            # 优先使用cross_principle作为关联解释，然后是reasoning
            reasoning = concept.get('cross_principle') or concept.get('reasoning', f"{source_concept}与{concept_name}相关")
            relation_type = concept.get('relation_type') or concept.get('relation', 'similar_to')
            
            # 创建节点
            node_id = generate_node_id(concept_name, discipline)
            nodes.append({
                "id": node_id,
                "label": concept_name,
                "discipline": discipline,
                "definition": definition[:200],  # 限制长度
                "credibility": credibility
            })
            
            # 创建边
            edges.append({
                "source": source_node_id,
                "target": node_id,
                "relation": relation_type,
                "weight": strength,
                "reasoning": reasoning[:500]  # 限制长度
            })
        
        metadata = calculate_graph_metrics(nodes, edges)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": metadata
        }
    
    async def merge_graphs(
        self,
        graph1: Dict[str, Any],
        graph2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并两个图谱
        
        Args:
            graph1: 图谱1
            graph2: 图谱2
            
        Returns:
            合并后的图谱
        """
        logger.info("Merging graphs")
        
        # 合并节点和边
        merged_nodes = merge_nodes(
            graph1.get('nodes', []),
            graph2.get('nodes', [])
        )
        
        merged_edges = merge_edges(
            graph1.get('edges', []),
            graph2.get('edges', [])
        )
        
        # 重新计算元数据
        metadata = calculate_graph_metrics(merged_nodes, merged_edges)
        metadata['merged_from'] = ['graph1', 'graph2']
        
        logger.info(f"Graphs merged: {len(merged_nodes)} nodes, {len(merged_edges)} edges")
        
        return {
            "nodes": merged_nodes,
            "edges": merged_edges,
            "metadata": metadata
        }
    
    async def expand_graph(
        self,
        existing_graph: Dict[str, Any],
        new_concepts: List[Dict[str, Any]],
        parent_node_id: str
    ) -> Dict[str, Any]:
        """
        扩展现有图谱
        
        Args:
            existing_graph: 现有图谱
            new_concepts: 新概念列表
            parent_node_id: 父节点ID
            
        Returns:
            扩展后的图谱
        """
        logger.info(f"Expanding graph from node: {parent_node_id}")
        
        # 找到父节点
        parent_node = next(
            (n for n in existing_graph.get('nodes', []) if n.get('id') == parent_node_id),
            None
        )
        
        if not parent_node:
            raise ValueError(f"Parent node not found: {parent_node_id}")
        
        parent_concept = parent_node.get('label', '')
        
        # 构建新图谱
        new_graph = await self.build_graph(parent_concept, new_concepts)
        
        # 合并图谱
        merged_graph = await self.merge_graphs(existing_graph, new_graph)
        
        logger.info("Graph expansion complete")
        
        return merged_graph
