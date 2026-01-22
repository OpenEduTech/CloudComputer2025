"""Neo4j图数据库客户端"""
import os
from typing import List, Dict, Any, Optional
from loguru import logger


class Neo4jClient:
    """Neo4j数据库客户端（支持Mock模式）"""
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.database = os.getenv("NEO4J_DATABASE", "conceptgraph")
        self.driver = None
        self.mock_mode = os.getenv("MOCK_DB", "true").lower() == "true"
        self._connected = False  # 添加连接状态标记
        
    async def connect(self):
        """连接到Neo4j数据库"""
        if self._connected:
            logger.debug("Neo4j已经连接，跳过重复连接")
            return
            
        if self.mock_mode:
            logger.info("[MOCK] Neo4j客户端运行在Mock模式")
            self._connected = True
            return
            
        try:
            from neo4j import AsyncGraphDatabase
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # 测试连接
            async with self.driver.session(database=self.database) as session:
                await session.run("RETURN 1")
            logger.info(f"已连接到Neo4j: {self.uri}")
            self._connected = True
        except ImportError:
            logger.warning("neo4j包未安装，切换到Mock模式")
            self.mock_mode = True
            self._connected = True
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}，切换到Mock模式")
            self.mock_mode = True
            self._connected = True
    
    async def disconnect(self):
        """断开连接"""
        if self.driver:
            await self.driver.close()
            logger.info("已断开Neo4j连接")
    
    async def is_connected(self) -> bool:
        """检查连接状态"""
        if self.mock_mode:
            return True
        return self.driver is not None
    
    async def query(self, cypher: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行Cypher查询"""
        if self.mock_mode:
            logger.debug(f"[MOCK] 执行查询: {cypher[:100]}...")
            return self._mock_query_result(cypher, parameters)
        
        # 如果driver为空但不是mock模式，尝试重新连接
        if not self.driver and not self.mock_mode:
            logger.warning("Neo4j driver为空，尝试重新连接...")
            await self.connect()
        
        if not self.driver:
            logger.error(f"Neo4j driver为空，mock_mode={self.mock_mode}, uri={self.uri}")
            raise RuntimeError("未连接到Neo4j数据库")
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(cypher, parameters or {})
            return [record.data() async for record in result]
    
    def _mock_query_result(self, cypher: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Mock查询结果"""
        # 根据查询类型返回不同的mock数据
        if "MATCH" in cypher.upper() and "RETURN" in cypher.upper():
            # 模拟节点查询
            return [
                {
                    "node": {
                        "id": "mock-1",
                        "label": "神经网络",
                        "discipline": "计算机科学",
                        "definition": "一种模仿生物神经网络的计算模型",
                        "credibility": 0.95
                    }
                },
                {
                    "node": {
                        "id": "mock-2",
                        "label": "深度学习",
                        "discipline": "人工智能",
                        "definition": "基于多层神经网络的机器学习方法",
                        "credibility": 0.92
                    }
                }
            ]
        elif "CREATE" in cypher.upper():
            # 模拟创建操作
            return [{"created": True}]
        else:
            return []
    
    async def create_concept_node(self, concept_data: Dict[str, Any]) -> str:
        """创建概念节点"""
        cypher = """
        MERGE (c:Concept {id: $id})
        SET c.label = $label,
            c.discipline = $discipline,
            c.definition = $definition,
            c.credibility = $credibility,
            c.created_at = timestamp(),
            c.updated_at = timestamp()
        RETURN c.id as id
        """
        result = await self.query(cypher, concept_data)
        return result[0]["id"] if result else concept_data["id"]
    
    async def create_concept_edge(self, edge_data: Dict[str, Any]) -> bool:
        """创建概念关系边"""
        cypher = """
        MATCH (s:Concept {id: $source})
        MATCH (t:Concept {id: $target})
        MERGE (s)-[r:RELATES {type: $relation}]->(t)
        SET r.weight = $weight,
            r.reasoning = $reasoning,
            r.created_at = timestamp(),
            r.updated_at = timestamp()
        RETURN r
        """
        result = await self.query(cypher, edge_data)
        return len(result) > 0
    
    async def get_concept_by_label(self, label: str) -> Optional[Dict[str, Any]]:
        """根据标签查询概念"""
        cypher = """
        MATCH (c:Concept {label: $label})
        RETURN c
        """
        result = await self.query(cypher, {"label": label})
        return result[0]["c"] if result else None
    
    async def get_related_concepts(self, concept_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        """获取关联概念"""
        cypher = f"""
        MATCH path = (c:Concept {{id: $concept_id}})-[*1..{depth}]-(related:Concept)
        RETURN DISTINCT related
        """
        result = await self.query(cypher, {"concept_id": concept_id})
        return [r["related"] for r in result]
    
    async def query_graph(self, concept_id: str) -> Dict[str, Any]:
        """查询指定概念的图谱数据"""
        if self.mock_mode:
            logger.debug(f"[MOCK] 查询图谱: {concept_id}")
            return {
                "nodes": [
                    {
                        "id": concept_id,
                        "label": "概念",
                        "discipline": "跨学科",
                        "definition": "Mock概念定义",
                        "credibility": 0.9,
                        "source": "LLM"
                    }
                ],
                "edges": []
            }
        
        # 查询节点
        nodes_cypher = """
        MATCH (c:Concept {id: $concept_id})
        OPTIONAL MATCH (c)-[r]-(related:Concept)
        RETURN DISTINCT c, related, r
        """
        result = await self.query(nodes_cypher, {"concept_id": concept_id})
        
        nodes = {}
        edges = []
        
        for record in result:
            if record.get("c"):
                c = record["c"]
                nodes[c["id"]] = c
            if record.get("related"):
                related = record["related"]
                nodes[related["id"]] = related
            if record.get("r"):
                r = record["r"]
                edges.append({
                    "source": concept_id,
                    "target": record["related"]["id"],
                    "relation": r.get("type", "related_to"),
                    "weight": r.get("weight", 0.5),
                    "reasoning": r.get("reasoning", "")
                })
        
        return {
            "nodes": list(nodes.values()),
            "edges": edges
        }
    
    async def search_concepts(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索概念"""
        if self.mock_mode:
            logger.debug(f"[MOCK] 搜索概念: {keyword}")
            return [
                {
                    "id": f"mock_{keyword}",
                    "label": keyword,
                    "discipline": "跨学科",
                    "definition": f"关于{keyword}的概念",
                    "credibility": 0.85,
                    "source": "LLM"
                }
            ]
        
        cypher = """
        MATCH (c:Concept)
        WHERE c.label CONTAINS $keyword OR c.definition CONTAINS $keyword
        RETURN c
        LIMIT $limit
        """
        result = await self.query(cypher, {"keyword": keyword, "limit": limit})
        return [r["c"] for r in result]
    
    async def get_all_disciplines(self) -> List[str]:
        """获取所有学科列表"""
        if self.mock_mode:
            return ["数学", "物理", "化学", "生物", "计算机科学", "社会学"]
        
        cypher = """
        MATCH (c:Concept)
        RETURN DISTINCT c.discipline as discipline
        """
        result = await self.query(cypher)
        return [r["discipline"] for r in result if r.get("discipline")]
    
    async def save_graph_data(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> bool:
        """批量保存图数据（节点和边）"""
        if self.mock_mode:
            logger.debug(f"[MOCK] 保存图数据: {len(nodes)}个节点, {len(edges)}条边")
            return True
        
        # 如果driver为空，尝试重新连接
        if not self.driver and not self.mock_mode:
            logger.warning("Neo4j driver为空，尝试重新连接...")
            await self.connect()
        
        if not self.driver:
            logger.error("Neo4j未连接，无法保存数据")
            return False
        
        try:
            async with self.driver.session(database=self.database) as session:
                # 批量创建节点
                for node in nodes:
                    await session.run("""
                        MERGE (c:Concept {id: $id})
                        SET c.label = $label,
                            c.discipline = $discipline,
                            c.definition = $definition,
                            c.brief_summary = $brief_summary,
                            c.credibility = $credibility,
                            c.source = $source,
                            c.wiki_url = $wiki_url,
                            c.updated_at = timestamp()
                        ON CREATE SET c.created_at = timestamp()
                    """, {
                        "id": node.get("id"),
                        "label": node.get("label"),
                        "discipline": node.get("discipline", "未分类"),
                        "definition": node.get("definition", ""),
                        "brief_summary": node.get("brief_summary", ""),
                        "credibility": node.get("credibility", 0.5),
                        "source": node.get("source", "LLM"),
                        "wiki_url": node.get("wiki_url", "")
                    })
                
                # 批量创建边
                for edge in edges:
                    await session.run("""
                        MATCH (s:Concept {id: $source})
                        MATCH (t:Concept {id: $target})
                        MERGE (s)-[r:RELATES]->(t)
                        SET r.relation = $relation,
                            r.weight = $weight,
                            r.reasoning = $reasoning,
                            r.updated_at = timestamp()
                        ON CREATE SET r.created_at = timestamp()
                    """, {
                        "source": edge.get("source"),
                        "target": edge.get("target"),
                        "relation": edge.get("relation", "related_to"),
                        "weight": edge.get("weight", 0.5),
                        "reasoning": edge.get("reasoning", "")
                    })
                
                logger.info(f"成功保存到Neo4j: {len(nodes)}个节点, {len(edges)}条边")
                return True
        except Exception as e:
            logger.error(f"保存到Neo4j失败: {e}")
            return False
    
    async def get_graph_by_concept(self, concept: str, max_depth: int = 2) -> Optional[Dict[str, Any]]:
        """根据概念标签获取完整子图（包含节点和边）"""
        if self.mock_mode:
            logger.debug(f"[MOCK] 查询子图: {concept}")
            return None
        
        # 如果driver为空，尝试重新连接
        if not self.driver and not self.mock_mode:
            logger.warning("Neo4j driver为空，尝试重新连接...")
            await self.connect()
        
        if not self.driver:
            return None
        
        try:
            async with self.driver.session(database=self.database) as session:
                # 查询中心节点及其关联节点和边
                # 注意：路径长度必须使用字面量，不能用参数
                result = await session.run(f"""
                    MATCH (center:Concept {{label: $concept}})
                    OPTIONAL MATCH path = (center)-[r:RELATES*1..{max_depth}]-(related:Concept)
                    WITH center, collect(DISTINCT related) as relateds, 
                         collect(DISTINCT r) as rels
                    RETURN center, relateds, rels
                """, {"concept": concept})
                
                record = await result.single()
                if not record or not record.get("center"):
                    logger.info(f"Neo4j中未找到概念: {concept}")
                    return None
                
                # 构建节点列表
                nodes = []
                center = dict(record["center"])
                nodes.append(center)
                
                if record.get("relateds"):
                    for related_node in record["relateds"]:
                        if related_node:
                            nodes.append(dict(related_node))
                
                # 构建边列表
                edges = []
                if record.get("rels"):
                    for rel_list in record["rels"]:
                        if rel_list:
                            for rel in (rel_list if isinstance(rel_list, list) else [rel_list]):
                                if rel:
                                    edges.append({
                                        "source": rel.start_node["id"],
                                        "target": rel.end_node["id"],
                                        "relation": dict(rel).get("relation", "related_to"),
                                        "weight": dict(rel).get("weight", 0.5),
                                        "reasoning": dict(rel).get("reasoning", "")
                                    })
                
                logger.info(f"从Neo4j加载图数据: {len(nodes)}个节点, {len(edges)}条边")
                return {
                    "nodes": nodes,
                    "edges": edges,
                    "source": "neo4j"
                }
        except Exception as e:
            logger.error(f"从Neo4j查询图数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None


# 全局实例
neo4j_client = Neo4jClient()
