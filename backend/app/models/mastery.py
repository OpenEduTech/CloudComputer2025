from typing import Optional

from pydantic import BaseModel


class Mastery(BaseModel):
    id: Optional[str] = None
    notebook_id: Optional[str] = None
    student_id: Optional[str] = None
    node_id: str

    seen: int = 0
    correct: int = 0
    wrong: int = 0

    mastery_score: float = 0.0
