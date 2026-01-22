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
    # Get recent results
    cursor = db.db.quiz_results.find({"user_id": str(current_user.id)}).sort("created_at", -1)
    history_data = await cursor.to_list(length=20)
    history = [QuizResult(**r) for r in history_data]
    
    analysis = await tutor_agent.analyze_mistakes(history)
    return analysis
