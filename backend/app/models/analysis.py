from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.user import PyObjectId

class WeakPoint(BaseModel):
    knowledge_point: str
    error_count: int
    error_types: List[str]

class MistakeAnalysisCache(BaseModel):
    """错题分析缓存模型"""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: PyObjectId
    weak_points: List[WeakPoint]
    recommendations: List[str]
    total_mistakes: int
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
