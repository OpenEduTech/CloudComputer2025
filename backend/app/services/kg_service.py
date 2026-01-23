from app.agent.kg_graph import kg_graph
from app.db.neo4j_conn import driver, init_neo4j, get_neo4j_driver
import json


class KnowledgeGraphService:
    @staticmethod
    def run_agent(concept: str):
        """触发Agent，自主完成输入校验→查库→扩展→校验→存库→生成图谱"""
        initial_state = {
            "concept": concept,
            "input_valid": False,
            "input_error_msg": "",
            "db_result": "",
            "new_relations": [],
            "valid_relations": [],
            "invalid_relations": [],
            "cleaned_relations": [],
            "final_graph": {},
            "reasoning": [],
            "expand_retry_count": 0
        }

        result = kg_graph.invoke(initial_state)

        if not result.get("input_valid"):
            return result["final_graph"]

        if not result.get("final_graph"):
            raise Exception("Agent执行失败，未生成图谱数据")

        return result["final_graph"]

    def query_db(self, concept):
        """仅从数据库查询已有合法关联（直接用Neo4j驱动，无工具调用）"""
        # 1. 严格的基础参数校验（确保抛出异常）
        if not isinstance(concept, str):
            raise Exception("核心概念必须是字符串类型")

        concept_stripped = concept.strip()
        if not concept_stripped:
            raise Exception("核心概念不能为空")

        print(concept_stripped)
        if len(concept_stripped) > 20:
            raise Exception("核心概念长度不能超过20字")
        driver = None
        try:
            driver = get_neo4j_driver()
        except Exception as e:
            print(f"❌ 重新初始化driver失败：{e}")

        # 3. 执行Neo4j查询
        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH (c:Concept {name: $concept})-[r:RELATION {is_valid: true}]->(related)
                    RETURN c.name as source,
                           collect({
                               target: related.name,
                               domain: related.domain,
                               relation: r.relation,
                               strength: r.strength,
                               version: COALESCE(r.version, 1)
                           }) as related_nodes
                """, concept=concept_stripped)

                record = result.single()
                if not record:
                    db_data = {"source": concept_stripped, "related_nodes": []}
                else:
                    db_data = record.data()

        except Exception as e:
            raise Exception(f"Neo4j查询失败：{str(e)}")

        # 4. 构建返回数据
        nodes = [{"name": concept_stripped, "domain": "未知"}]
        links = []

        for rel in db_data["related_nodes"]:
            if rel.get("strength", 0) >= 2:
                nodes.append({"name": rel["target"], "domain": rel["domain"]})
                links.append({
                    "source": concept_stripped,
                    "target": rel["target"],
                    "relation": rel["relation"],
                    "strength": rel["strength"]
                })

        nodes = [dict(t) for t in {tuple(d.items()) for d in nodes}]

        return {
            "code": 200,
            "msg": "数据库查询成功",
            "nodes": nodes,
            "links": links,
            "reasoning": [f"仅查库：获取{concept_stripped}的已有关联（直接访问Neo4j，无LLM调用）"],
            "cleaned_relations": [],
            "has_data": len(links) > 0
        }


kg_service = KnowledgeGraphService()