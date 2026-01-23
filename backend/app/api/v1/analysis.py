from fastapi import APIRouter, Depends
from app.api import deps
from app.models.user import UserResponse
from app.core.database import db
from app.services.agents.tutor import tutor_agent
from app.models.quiz import QuizResult
from typing import Dict

router = APIRouter()

@router.get("/mistakes")
async def get_mistake_analysis(current_user: UserResponse = Depends(deps.get_current_user)) -> Dict:
    """
    获取错题分析
    优先使用缓存，缓存不存在或过期时重新分析
    """
    analysis = await tutor_agent.get_cached_analysis(str(current_user.id))
    return analysis

@router.post("/mistakes/refresh")
async def refresh_mistake_analysis(current_user: UserResponse = Depends(deps.get_current_user)) -> Dict:
    """
    强制刷新错题分析
    用户可以手动触发重新分析
    """
    analysis = await tutor_agent.update_analysis_cache(str(current_user.id))
    return analysis
