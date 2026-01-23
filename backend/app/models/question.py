from typing import List, Optional

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: Optional[str] = None
    quiz_id: str
    type: str  # mcq/short
    stem: str
    options: Optional[List[str]] = None
    answer_key: str
    rubric: Optional[str] = None
    difficulty: str
    material_ids: List[str] = Field(default_factory=list)
    knowledge_points: List[str] = Field(default_factory=list)
    # M2：该题关联到哪些知识节点（用于掌握度回流）
    node_ids: List[str] = Field(default_factory=list)
    analysis: Optional[str] = None
