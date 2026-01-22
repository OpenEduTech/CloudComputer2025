from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Attempt(BaseModel):
    id: Optional[str] = None
    quiz_id: str
    student_id: str
    status: str = "grading"
    answers: Dict[str, Any] = Field(default_factory=dict)
    grading: Optional[List[Dict[str, Any]]] = None
    score: Optional[float] = None
    created_at: Optional[datetime] = None
    error_message: Optional[str] = None
