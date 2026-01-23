from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.kg_service import kg_service

router = APIRouter()


class ConceptRequest(BaseModel):
    concept: str


@router.post("/api/kg/query-db")
async def query_kg_from_db(request: ConceptRequest):
    """仅查询数据库中已有的合法知识图谱（直接访问Neo4j，无LLM调用）"""
    # 基础校验
    concept = request.concept.strip()
    if not concept:
        raise HTTPException(status_code=400, detail="核心概念不能为空")
    if len(concept) > 20:
        raise HTTPException(status_code=400, detail="核心概念长度不能超过20字")

    # 调用服务层的query_db方法（直接访问Neo4j）
    try:
        db_graph = kg_service.query_db(concept)
        return {
            "code": 200,
            "data": db_graph,
            "msg": db_graph["msg"],
            "has_data": db_graph["has_data"]  # 前端判断关键
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询数据库失败：{str(e)}")

@router.post("/api/kg/generate")
async def generate_kg(request: ConceptRequest):
    # 1. 仅保留基础校验
    concept = request.concept.strip()

    # 空值校验
    if not concept:
        raise HTTPException(status_code=400, detail="核心概念不能为空")

    # 长度校验
    if len(concept) > 20:
        raise HTTPException(status_code=400, detail="核心概念长度不能超过20字")

    # 2. 调用Agent生成图谱（输入有效性由Agent自主判断）
    try:
        final_graph = kg_service.run_agent(concept)
        # 若Agent返回无效输入提示，直接返回400
        if final_graph.get("code") == 400:
            raise HTTPException(status_code=400, detail=final_graph["msg"])

        # 提取final_graph中的核心字段（完全匹配期望格式）
        nodes = final_graph.get("nodes", [])
        links = final_graph.get("links", [])
        reasoning = final_graph.get("reasoning", [])
        cleaned_relations = final_graph.get("cleaned_relations", [])

        # 统计节点/链路数量
        node_count = len(nodes)
        link_count = len(links)

        # 3. 返回完全符合期望格式的结果
        return {
            "code": 200,
            "data": {
                "nodes": nodes,
                "links": links,
                "reasoning": reasoning,
                "cleaned_relations": cleaned_relations
            },
            "msg": f"成功生成{node_count}个节点、{link_count}条合法关联"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")