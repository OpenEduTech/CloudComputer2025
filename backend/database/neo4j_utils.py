import logging
import traceback
from neo4j import GraphDatabase
from config import settings

# 初始化 Driver
driver = None

# Setup logging
logger = logging.getLogger("neo4j_utils")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def get_driver():
    global driver
    if not driver:
        try:
            driver = GraphDatabase.driver(
                settings.NEO4J_URI, 
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        except Exception as e:
            print(f"Error initializing Neo4j driver: {e}")
    return driver

def close_driver():
    global driver
    if driver:
        driver.close()

def query_node_and_neighbors(node_id: str, depth: int = 1):
    """
    根据 node_id 和 depth 查询节点及其邻居。
    """
    driver = get_driver()
    if not driver:
        logger.error("Neo4j driver is not initialized.")
        return None

    logger.info(f"Querying graph for node_id: {node_id}, depth: {depth}")

    # --- 重新实现查询逻辑：直接查三元组列表 ---
    # 这种方式对于处理图数据更直观
    
    # 查询所有涉及的边
    basic_path_query = f"""
    MATCH (startNode:Entity) 
    WHERE startNode.id = $node_id OR toLower(startNode.label) CONTAINS toLower($node_id)
    WITH startNode LIMIT 1
    MATCH p = (startNode)-[*0..{depth}]-(endNode:Entity)
    UNWIND relationships(p) as rel
    WITH startNode, endNode, rel
    RETURN startNode(rel) as source, rel, endNode(rel) as target
    LIMIT 500
    """
    
    # 还是需要把单独的 startNode 也查出来（以防孤立点）
    single_node_query = f"""
    MATCH (n:Entity) 
    WHERE n.id = $node_id OR toLower(n.label) CONTAINS toLower($node_id)
    RETURN n LIMIT 1
    """

    final_nodes = {}
    final_links = []
    links_set = set()

    try:
        with driver.session() as session:
            # 1. 确保中心节点存在
            logger.info("Executing center node query...")
            center_res = list(session.run(single_node_query, node_id=node_id))
            if not center_res:
                logger.warning(f"No center node found for: {node_id}")
                return {"nodes": [], "links": []}
            
            center_node = dict(center_res[0]["n"])
            final_nodes[center_node["id"]] = center_node
            
            # 2. 查询路径
            logger.info("Executing path query...")
            path_res = list(session.run(basic_path_query, node_id=node_id))
            logger.info(f"Found {len(path_res)} paths.")
            
            for record in path_res:
                try:
                    source = dict(record["source"])
                    target = dict(record["target"])
                    rel = record["rel"]
                    
                    final_nodes[source["id"]] = source
                    final_nodes[target["id"]] = target
                    
                    # 兼容处理 relation 属性
                    # 如果 rel 是 neo4j.graph.Relationship 对象，使用 .type
                    # 如果是 dict (通常不会，除非 apoc)，使用 ["relation"]
                    rel_type = rel.type if hasattr(rel, 'type') else rel.get("relation", "RELATED_TO")
                    
                    link_key = (source["id"], target["id"], rel_type)
                    if link_key not in links_set:
                        links_set.add(link_key)
                        final_links.append({
                            "source": source["id"],
                            "target": target["id"],
                            "relation": rel_type,
                            "desc": rel.get("desc", ""),
                            "citation": rel.get("citation", "")
                        })
                except Exception as inner_e:
                    logger.error(f"Error processing record: {inner_e}")
                    logger.error(f"Record content: {record}")
                    continue

    except Exception as e:
        logger.error(f"Neo4j Query Error: {e}")
        logger.error(traceback.format_exc())
        raise e

    logger.info(f"Returning {len(final_nodes)} nodes and {len(final_links)} links.")
    return {
        "nodes": list(final_nodes.values()),
        "links": final_links
    }
