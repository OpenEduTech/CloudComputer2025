import logging
from fastapi import APIRouter, HTTPException, Query
from database.neo4j_utils import query_node_and_neighbors

# Setup logging
logger = logging.getLogger("graph_router")
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/api/graph",
    tags=["graph"]
)

@router.get("/{node_id}")
def get_graph_data(node_id: str, depth: int = Query(1, ge=1, le=5)):
    """
    从 Neo4j 获取图谱数据
    """
    logger.info(f"Received graph request for node_id: {node_id}, depth: {depth}")
    try:
        data = query_node_and_neighbors(node_id, depth)
        if data is None:
             logger.error("Neo4j service returned None (unavailable)")
             raise HTTPException(status_code=503, detail="Neo4j service unavailable")
        
        # 即使数据为空，也返回空结构，而不是 500
        logger.info(f"Successfully retrieved graph data with {len(data.get('nodes', []))} nodes")
        return data
    except Exception as e:
        logger.error(f"Internal Server Error in get_graph_data: {e}")
        # 不直接暴露内部错误给前端，但为了调试，这里先打印
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
