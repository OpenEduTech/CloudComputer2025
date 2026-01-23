from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional
from app.models.graph import GraphBuildRequest, GraphBuildResponse
from app.services.graph_service import graph_service
from app.services.task_service import task_service
from app.core.schema import validator
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def process_graph_task(task_id: str, concept: str):
    """后台处理图谱生成任务"""
    # 更新任务状态为运行中
    task_service.update_task(task_id, {"status": "running", "progress": 30})
    
    try:
        # 1. 生成图谱数据
        graph_data = graph_service.generate_mock_graph(concept)
        
        # 2. 标准化处理
        normalized_data = graph_service.normalize_graph(graph_data)
        
        # 3. 验证Schema
        is_valid, message = validator.validate(normalized_data)
        if not is_valid:
            raise ValueError(f"Schema验证失败: {message}")
        
        # 4. 保存到存储
        graph_service.save_to_neo4j(normalized_data)
        graph_service.save_to_cache(concept, normalized_data)
        
        # 5. 更新任务状态为成功
        task_service.update_task(task_id, {
            "status": "success",
            "progress": 100,
            "result": normalized_data
        })
        
        logger.info(f"✅ 图谱生成完成: {concept}")
        
    except Exception as e:
        logger.error(f"图谱生成失败: {e}")
        task_service.update_task(task_id, {
            "status": "failed",
            "progress": 100,
            "error_message": str(e)
        })

@router.post("/build", response_model=GraphBuildResponse)
async def build_graph(
    request: GraphBuildRequest,
    background_tasks: BackgroundTasks
):
    """生成跨学科知识图谱"""
    
    # 检查缓存
    if not request.force_refresh:
        cached_data = graph_service.get_from_cache(request.concept)
        if cached_data:
            return GraphBuildResponse(
                task_id="cached",
                status="success",
                message="命中缓存，直接返回",
                estimated_time=0
            )
    
    # 创建任务
    task_id = task_service.create_task(request.concept)
    if not task_id:
        raise HTTPException(status_code=500, detail="任务创建失败")
    
    # 在后台处理任务
    background_tasks.add_task(process_graph_task, task_id, request.concept)
    
    return GraphBuildResponse(
        task_id=task_id,
        status="pending",
        message="任务已提交，正在后台处理",
        estimated_time=10  # 预估10秒
    )

@router.get("/query")
async def query_graph(
    concept: str = Query(..., description="核心概念词"),
    use_cache: bool = Query(True, description="是否使用缓存")
):
    """查询知识图谱"""
    
    # 从缓存获取
    if use_cache:
        cached_data = graph_service.get_from_cache(concept)
        if cached_data:
            return {
                "status": "success",
                "message": "命中缓存",
                "data": cached_data,
                "source": "cache"
            }
    
    # 从Neo4j获取（TODO：实现Neo4j查询）
    # 暂时返回Mock数据
    graph_data = graph_service.generate_mock_graph(concept)
    
    return {
        "status": "success",
        "message": "生成新的图谱数据",
        "data": graph_data,
        "source": "generated"
    }

@router.get("/schema")
async def get_schema():
    """获取GraphJSON Schema信息"""
    schema_info = validator.get_schema_info()
    return {
        "status": "success",
        "schema_info": schema_info
    }

@router.get("/statistics")
async def get_statistics():
    """获取系统统计信息"""
    try:
        # 统计缓存中的图谱数量
        cache_keys = graph_service.redis_client.keys(f"{graph_service.cache_prefix}*")
        
        return {
            "status": "success",
            "statistics": {
                "cached_graphs": len(cache_keys),
                "cache_prefix": graph_service.cache_prefix,
                "cache_ttl": graph_service.settings.CACHE_TTL
            }
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))