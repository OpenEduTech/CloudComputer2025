"""
Neo4j客户端（增强版）
- 适配 Docker Neo4j/本地 Neo4j（由 .env 的 NEO4J_URI/USER/PASSWORD 决定）
- 更稳健的 MERGE 策略：按 (name, discipline) 合并节点；按 (src, tgt, relation) 合并边
- 存储属性：level/type/description/confidence
"""
from __future__ import annotations
from typing import Dict, Any
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, exceptions

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

class LocalNeo4jClient:
    def __init__(self):
        if not NEO4J_PASSWORD:
            raise RuntimeError("NEO4J_PASSWORD 未设置（请在 .env 或 docker compose 环境变量中配置）")
        self.driver = GraphDatabase.driver(
            uri=NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        self.driver.verify_connectivity()

    def close(self):
        if self.driver:
            self.driver.close()

    def clear_local_data(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def import_to_local_neo4j(self, graph: Dict[str, Any]):
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        with self.driver.session() as session:
            # nodes
            for n in nodes:
                session.run(
                    """
                    MERGE (c:Concept {name: $name, discipline: $discipline})
                    SET c.level=$level,
                        c.type=$type,
                        c.description=$description,
                        c.confidence=$confidence
                    """,
                    name=n.get("name"),
                    discipline=n.get("discipline"),
                    level=int(n.get("level", 1)),
                    type=n.get("type","concept"),
                    description=n.get("description",""),
                    confidence=float(n.get("confidence", 0.6)),
                )

            # edges
            # 先构造 id->(name,discipline)
            id_to_node = {n["id"]: n for n in nodes}
            for e in edges:
                s = id_to_node.get(e.get("source"))
                t = id_to_node.get(e.get("target"))
                if not s or not t:
                    continue
                session.run(
                    """
                    MATCH (a:Concept {name: $sname, discipline: $sdisc})
                    MATCH (b:Concept {name: $tname, discipline: $tdisc})
                    MERGE (a)-[r:REL {relation: $relation}]->(b)
                    SET r.logic=$logic,
                        r.confidence=$confidence
                    """,
                    sname=s["name"], sdisc=s["discipline"],
                    tname=t["name"], tdisc=t["discipline"],
                    relation=e.get("relation","RELATES_TO"),
                    logic=e.get("logic",""),
                    confidence=float(e.get("confidence", 0.6))
                )
