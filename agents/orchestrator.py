"""Agent编排器 - 协调三个Agent的工作流程"""

import time
import logging
from typing import List, Dict, Any, Optional
from agents.concept_discovery_agent import ConceptDiscoveryAgent
from agents.verification_agent import VerificationAgent
from agents.graph_builder_agent import GraphBuilderAgent
from shared.schemas import DiscoverResponse, GraphData, Metadata
from shared.utils import generate_request_id
from shared.constants import Discipline, AgentConfig
from agents.utils import ProgressTracker

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Agent编排器
    
    协调三个Agent的工作流程：
    1. ConceptDiscoveryAgent - 发现跨学科相关概念
    2. VerificationAgent - 验证概念关联的准确性
    3. GraphBuilderAgent - 构建知识图谱
    """
    
    def __init__(self):
        """初始化三个Agent"""
        self.discovery_agent = ConceptDiscoveryAgent()
        self.verification_agent = VerificationAgent()
        self.graph_builder_agent = GraphBuilderAgent()
        
        logger.info("AgentOrchestrator initialized")
    
    async def discover(
        self,
        concept: str,
        disciplines: Optional[List[str]] = None,
        depth: int = AgentConfig.DEFAULT_DEPTH,
        max_concepts: int = AgentConfig.DEFAULT_MAX_CONCEPTS,
        enable_verification: bool = True,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> DiscoverResponse:
        """
        执行完整的概念挖掘流程
        
        Args:
            concept: 核心概念
            disciplines: 目标学科列表
            depth: 挖掘深度
            max_concepts: 最大概念数
            enable_verification: 是否启用知识校验
            progress_tracker: 进度追踪器
            
        Returns:
            API响应
        """
        request_id = generate_request_id()
        start_time = time.time()
        
        logger.info(f"[{request_id}] Starting discovery for concept: {concept}")
        
        if not progress_tracker:
            progress_tracker = ProgressTracker(request_id)
        
        try:
            # 验证输入
            if not concept or not concept.strip():
                raise ValueError("Concept cannot be empty")
            
            if not disciplines:
                disciplines = Discipline.ALL
            
            # 阶段1: 概念挖掘
            await progress_tracker.update(
                stage="discovering",
                progress=10,
                message=f"正在分析概念：{concept}"
            )
            
            discovery_result = await self.discovery_agent.discover_concepts(
                concept=concept,
                disciplines=disciplines,
                depth=depth,
                max_concepts=max_concepts
            )
            
            related_concepts = discovery_result.get('related_concepts', [])
            
            if not related_concepts:
                logger.warning(f"[{request_id}] No concepts found")
                return DiscoverResponse(
                    status="success",
                    request_id=request_id,
                    message=f"未找到与'{concept}'相关的概念",
                    data=GraphData(
                        nodes=[],
                        edges=[],
                        metadata=Metadata(
                            total_nodes=0,
                            total_edges=0,
                            verified_nodes=0,
                            avg_credibility=0.0,
                            processing_time=time.time() - start_time
                        )
                    )
                )
            
            await progress_tracker.update(
                stage="discovering",
                progress=40,
                message=f"发现 {len(related_concepts)} 个相关概念"
            )
            
            # 阶段2: 知识校验（可选）
            if enable_verification:
                await progress_tracker.update(
                    stage="verifying",
                    progress=50,
                    message="正在验证概念关联的准确性"
                )
                
                verified_concepts = await self.verification_agent.verify_concepts(
                    concepts=related_concepts,
                    source_concept=concept
                )
                
                await progress_tracker.update(
                    stage="verifying",
                    progress=70,
                    message=f"验证完成：{len(verified_concepts)}/{len(related_concepts)} 通过"
                )
            else:
                # 跳过验证，使用默认可信度
                verified_concepts = related_concepts
                for c in verified_concepts:
                    c.setdefault('credibility', c.get('strength', 0.5))
                
                await progress_tracker.update(
                    stage="verifying",
                    progress=70,
                    message="跳过验证步骤"
                )
            
            # 阶段3: 图谱构建
            await progress_tracker.update(
                stage="building",
                progress=80,
                message="正在构建知识图谱"
            )
            
            graph_data = await self.graph_builder_agent.build_graph(
                source_concept=concept,
                verified_concepts=verified_concepts
            )
            
            # 计算处理时间
            processing_time = time.time() - start_time
            graph_data['metadata']['processing_time'] = round(processing_time, 2)
            
            await progress_tracker.update(
                stage="complete",
                progress=100,
                message="图谱构建完成"
            )
            
            logger.info(
                f"[{request_id}] Discovery complete: "
                f"{graph_data['metadata']['total_nodes']} nodes, "
                f"{graph_data['metadata']['total_edges']} edges, "
                f"{processing_time:.2f}s"
            )
            
            # 构建响应
            return DiscoverResponse(
                status="success",
                request_id=request_id,
                data=GraphData(
                    nodes=graph_data['nodes'],
                    edges=graph_data['edges'],
                    metadata=Metadata(**graph_data['metadata'])
                )
            )
            
        except Exception as e:
            logger.error(f"[{request_id}] Discovery failed: {str(e)}", exc_info=True)
            
            await progress_tracker.update(
                stage="error",
                progress=0,
                message=f"处理失败: {str(e)}"
            )
            
            return DiscoverResponse(
                status="error",
                request_id=request_id,
                message=str(e),
                error_code="ERR_2001"
            )
    
    async def expand(
        self,
        node_id: str,
        existing_graph: Dict[str, Any],
        disciplines: Optional[List[str]] = None,
        max_new_nodes: int = 10
    ) -> Dict[str, Any]:
        """
        扩展现有图谱的节点
        
        Args:
            node_id: 要扩展的节点ID
            existing_graph: 现有图谱
            disciplines: 目标学科列表
            max_new_nodes: 最多新增节点数
            
        Returns:
            扩展后的图谱
        """
        request_id = generate_request_id()
        logger.info(f"[{request_id}] Expanding node: {node_id}")
        
        try:
            # 找到要扩展的节点
            target_node = next(
                (n for n in existing_graph.get('nodes', []) if n.get('id') == node_id),
                None
            )
            
            if not target_node:
                raise ValueError(f"Node not found: {node_id}")
            
            parent_concept = target_node.get('label', '')
            parent_discipline = target_node.get('discipline', '')
            
            # 扩展节点
            expansion_result = await self.discovery_agent.expand_node(
                parent_concept=parent_concept,
                parent_discipline=parent_discipline,
                target_disciplines=disciplines,
                max_new_nodes=max_new_nodes
            )
            
            new_concepts = expansion_result.get('new_concepts', [])
            
            # 验证新概念
            verified_concepts = await self.verification_agent.verify_concepts(
                concepts=new_concepts,
                source_concept=parent_concept
            )
            
            # 扩展图谱
            expanded_graph = await self.graph_builder_agent.expand_graph(
                existing_graph=existing_graph,
                new_concepts=verified_concepts,
                parent_node_id=node_id
            )
            
            logger.info(f"[{request_id}] Expansion complete: {len(verified_concepts)} new concepts")
            
            return expanded_graph
            
        except Exception as e:
            logger.error(f"[{request_id}] Expansion failed: {str(e)}")
            raise
    
    async def verify(
        self,
        concept_a: str,
        concept_b: str,
        claimed_relation: str,
        strength: float = 0.5
    ) -> Dict[str, Any]:
        """
        验证概念关联
        
        Args:
            concept_a: 概念A
            concept_b: 概念B
            claimed_relation: 声称的关联
            strength: 声称的强度
            
        Returns:
            验证结果
        """
        request_id = generate_request_id()
        logger.info(f"[{request_id}] Verifying: {concept_a} -> {concept_b}")
        
        try:
            result = await self.verification_agent.verify_relation(
                concept_a=concept_a,
                concept_b=concept_b,
                claimed_relation=claimed_relation,
                strength=strength
            )
            
            return {
                "status": "success",
                "request_id": request_id,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"[{request_id}] Verification failed: {str(e)}")
            return {
                "status": "error",
                "request_id": request_id,
                "message": str(e),
                "error_code": "ERR_2004"
            }


# 全局编排器实例
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """获取全局编排器实例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
