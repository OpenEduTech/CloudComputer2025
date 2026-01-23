"""
主程序（增强版）：本地/容器均可运行
流程：Agent 生成结构化图谱 → Neo4j 导入 → 保存 JSON
"""
import json
from agent import get_agent
from neo4j_client import LocalNeo4jClient

def run_pipeline(core_concept: str = "最小二乘法", save_path: str | None = None, write_neo4j: bool = True):
    print(f"\n🚀 开始运行：构建【{core_concept}】跨学科知识图谱（增强版）")
    agent = get_agent()
    graph = agent.generate_graph(core_concept)
    print(f"📊 图谱统计：节点 {graph['node_count']} 个，边 {graph['edge_count']} 条")

    if write_neo4j:
        neo = LocalNeo4jClient()
        try:
            neo.clear_local_data()
            neo.import_to_local_neo4j(graph)
            print("✅ Neo4j 导入成功")
        finally:
            neo.close()

    if save_path is None:
        save_path = f"{core_concept}_graph.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存：{save_path}")

if __name__ == "__main__":
    run_pipeline("最小二乘法")
