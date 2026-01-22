"""
Neo4j客户端
管理图数据库连接和操作
"""
import os
import logging
from typing import Dict, Any, List, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j客户端类"""
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password123")
        
        self.driver: Optional[AsyncDriver] = None
        logger.info(f"Neo4j Client initialized with URI: {self.uri}")
    
    async def connect(self):
        """建立数据库连接"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # 验证连接
            await self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j")
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise
    
    async def close(self):
        """关闭数据库连接"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")
    
    async def create_graph(
        self,
        graph_id: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> bool:
        """
        创建知识图谱
        
        Args:
            graph_id: 图谱ID
            nodes: 节点列表
            edges: 边列表
            
        Returns:
            是否成功
        """
        if not self.driver:
            await self.connect()
        
        async with self.driver.session() as session:
            try:
                # 创建节点
                for node in nodes:
                    await session.run(
                        """
                        MERGE (n:Concept {id: $id, graph_id: $graph_id})
                        SET n.label = $label,
                            n.domain = $domain,
                            n.type = $type,
                            n.definition = $definition,
                            n.keywords = $keywords
                        """,
                        id=node.get("id"),
                        graph_id=graph_id,
                        label=node.get("label"),
                        domain=node.get("domain"),
                        type=node.get("type", "related"),
                        definition=node.get("definition", ""),
                        keywords=node.get("keywords", [])
                    )
                
                # 创建关系
                for edge in edges:
                    await session.run(
                        """
                        MATCH (a:Concept {id: $source, graph_id: $graph_id})
                        MATCH (b:Concept {id: $target, graph_id: $graph_id})
                        MERGE (a)-[r:RELATES_TO {id: $edge_id}]->(b)
                        SET r.relation_type = $relation_type,
                            r.strength = $strength,
                            r.explanation = $explanation,
                            r.confidence = $confidence
                        """,
                        source=edge.get("source"),
                        target=edge.get("target"),
                        graph_id=graph_id,
                        edge_id=edge.get("id"),
                        relation_type=edge.get("relation_type"),
                        strength=edge.get("strength", 5),
                        explanation=edge.get("explanation", ""),
                        confidence=edge.get("confidence", 1.0)
                    )
                
                logger.info(f"Created graph {graph_id} with {len(nodes)} nodes and {len(edges)} edges")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create graph: {str(e)}")
                raise
    
    async def get_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """
        获取知识图谱
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            图谱数据
        """
        if not self.driver:
            await self.connect()
        
        async with self.driver.session() as session:
            try:
                # 获取节点
                nodes_result = await session.run(
                    """
                    MATCH (n:Concept {graph_id: $graph_id})
                    RETURN n.id as id, n.label as label, n.domain as domain,
                           n.type as type, n.definition as definition,
                           n.keywords as keywords
                    """,
                    graph_id=graph_id
                )
                
                nodes = []
                async for record in nodes_result:
                    nodes.append({
                        "id": record["id"],
                        "label": record["label"],
                        "domain": record["domain"],
                        "type": record["type"],
                        "definition": record.get("definition", ""),
                        "keywords": record.get("keywords", [])
                    })
                
                if not nodes:
                    return None
                
                # 获取边
                edges_result = await session.run(
                    """
                    MATCH (a:Concept {graph_id: $graph_id})-[r:RELATES_TO]->(b:Concept {graph_id: $graph_id})
                    RETURN r.id as id, a.id as source, b.id as target,
                           r.relation_type as relation_type, r.strength as strength,
                           r.explanation as explanation, r.confidence as confidence
                    """,
                    graph_id=graph_id
                )
                
                edges = []
                async for record in edges_result:
                    edges.append({
                        "id": record["id"],
                        "source": record["source"],
                        "target": record["target"],
                        "relation_type": record["relation_type"],
                        "strength": record["strength"],
                        "explanation": record["explanation"],
                        "confidence": record.get("confidence", 1.0)
                    })
                
                return {
                    "nodes": nodes,
                    "edges": edges
                }
                
            except Exception as e:
                logger.error(f"Failed to get graph: {str(e)}")
                raise
    
    async def expand_node(
        self,
        graph_id: str,
        node_id: str,
        new_nodes: List[Dict[str, Any]],
        new_edges: List[Dict[str, Any]]
    ) -> bool:
        """
        扩展图谱节点
        
        Args:
            graph_id: 图谱ID
            node_id: 要扩展的节点ID
            new_nodes: 新节点列表
            new_edges: 新边列表
            
        Returns:
            是否成功
        """
        if not self.driver:
            await self.connect()
        
        async with self.driver.session() as session:
            try:
                # 添加新节点
                for node in new_nodes:
                    await session.run(
                        """
                        MERGE (n:Concept {id: $id, graph_id: $graph_id})
                        SET n.label = $label,
                            n.domain = $domain,
                            n.type = $type
                        """,
                        id=node.get("id"),
                        graph_id=graph_id,
                        label=node.get("label"),
                        domain=node.get("domain"),
                        type=node.get("type", "related")
                    )
                
                # 添加新边
                for edge in new_edges:
                    await session.run(
                        """
                        MATCH (a:Concept {id: $source, graph_id: $graph_id})
                        MATCH (b:Concept {id: $target, graph_id: $graph_id})
                        MERGE (a)-[r:RELATES_TO {id: $edge_id}]->(b)
                        SET r.relation_type = $relation_type,
                            r.strength = $strength,
                            r.explanation = $explanation,
                            r.confidence = $confidence
                        """,
                        source=edge.get("source"),
                        target=edge.get("target"),
                        graph_id=graph_id,
                        edge_id=edge.get("id"),
                        relation_type=edge.get("relation_type"),
                        strength=edge.get("strength", 5),
                        explanation=edge.get("explanation", ""),
                        confidence=edge.get("confidence", 1.0)
                    )
                
                logger.info(f"Expanded node {node_id} in graph {graph_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to expand node: {str(e)}")
                raise
    
    async def delete_graph(self, graph_id: str) -> bool:
        """删除图谱"""
        if not self.driver:
            await self.connect()
        
        async with self.driver.session() as session:
            try:
                await session.run(
                    """
                    MATCH (n:Concept {graph_id: $graph_id})
                    DETACH DELETE n
                    """,
                    graph_id=graph_id
                )
                
                logger.info(f"Deleted graph {graph_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to delete graph: {str(e)}")
                raise
    
    async def list_graphs(self) -> List[str]:
        """列出所有图谱ID"""
        if not self.driver:
            await self.connect()
        
        async with self.driver.session() as session:
            try:
                result = await session.run(
                    """
                    MATCH (n:Concept)
                    RETURN DISTINCT n.graph_id as graph_id
                    """
                )
                
                graph_ids = []
                async for record in result:
                    if record["graph_id"]:
                        graph_ids.append(record["graph_id"])
                
                return graph_ids
                
            except Exception as e:
                logger.error(f"Failed to list graphs: {str(e)}")
                raise

