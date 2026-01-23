from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Mistake(BaseModel):
    id: Optional[str] = None
    notebook_id: Optional[str] = None
    student_id: str
    question_id: str
    wrong_count: int = 0
    # M3: persist missing_points from grading so Coach can be grounded
    missing_points: List[str] = Field(default_factory=list)
    error_tags: List[str] = Field(default_factory=list)
    knowledge_points: List[str] = Field(default_factory=list)
    last_error_analysis: Optional[str] = None
    last_wrong_at: Optional[datetime] = None
    last_question: Optional[str] = None
    last_question_type: Optional[str] = None
    last_options: List[str] = Field(default_factory=list)
    last_student_answer: Optional[str] = None
    last_correct_answer: Optional[str] = None
    last_explanation: Optional[str] = None
