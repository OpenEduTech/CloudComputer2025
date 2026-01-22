from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Quiz(BaseModel):
    id: Optional[str] = None
    student_id: str
    notebook_id: str
    material_ids: List[str] = Field(default_factory=list)
    # M2：按知识点/章节范围出题（可选）
    node_id: Optional[str] = None
    status: str = "generating"
    question_ids: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    error_message: Optional[str] = None
