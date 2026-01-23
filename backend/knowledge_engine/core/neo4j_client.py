import os
import logging
from typing import List, Dict, Any
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("neo4j-client")

class Neo4jClient:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password123")
        self.driver = None

    async def connect(self):
        """建立连接"""
        if not self.driver:
            try:
                self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
                logger.info(" Connected to Neo4j")
            except Exception as e:
                logger.error(f" Failed to connect to Neo4j: {e}")

    async def close(self):
        """关闭连接"""
        if self.driver:
            await self.driver.close()
            self.driver = None

    async def verify_connectivity(self):
        """验证连接是否可用"""
        if not self.driver:
            await self.connect()
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    async def save_graph(self, concept: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        """
        将图谱数据保存到 Neo4j
        策略：
        1. 节点使用 MERGE (避免重复)
        2. 边使用 MERGE
        3. 为该 Concept 打上标签，方便后续按概念查询
        """
        if not self.driver:
            await self.connect()

        async with self.driver.session() as session:
            # 1. 批量插入节点 
            
            node_query = """
            UNWIND $nodes AS row
            MERGE (n:Entity {id: row.id})
            SET n.label = row.label,
                n.description = row.description,
                n.size = row.size,
                n.domains = row.domains,
                n.source_chunks = row.source_chunks,
                n.last_updated = datetime()
            // 建立该节点与核心概念的关联属性 (可选)
            """
            
            try:
                await session.run(node_query, nodes=nodes)
                logger.info(f"Saved {len(nodes)} nodes to Neo4j for '{concept}'")
            except Exception as e:
                logger.error(f"Error saving nodes: {e}")
                raise e

            # 2. 批量插入边 。
            
            edge_query = """
            UNWIND $edges AS row
            MATCH (source:Entity {id: row.source})
            MATCH (target:Entity {id: row.target})
            MERGE (source)-[r:RELATED]->(target)
            SET r.label = row.relation,
                r.description = row.description,
                r.concept = $concept,
                r.last_updated = datetime()
            """
            
            try:
                await session.run(edge_query, edges=edges, concept=concept)
                logger.info(f"Saved {len(edges)} edges to Neo4j for '{concept}'")
            except Exception as e:
                logger.error(f"Error saving edges: {e}")
                raise e

# 单例模式
neo4j_client = Neo4jClient()