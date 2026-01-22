from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.task_service import task_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/status")
async def get_task_status(
    task_id: str = Query(..., description="任务ID")
):
    """查询任务状态"""
    task_data = task_service.get_task(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    
    return {
        "status": "success",
        "task": task_data
    }

@router.get("/list")
async def list_tasks(
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    status: Optional[str] = Query(None, description="按状态过滤")
):
    """列出任务（简化实现）"""
    # 注意：Redis不适合直接列出所有任务
    # 实际项目中应该用专门的数据库表
    return {
        "status": "success",
        "message": "TODO: 实现任务列表查询",
        "tasks": [],
        "total": 0,
        "limit": limit
    }