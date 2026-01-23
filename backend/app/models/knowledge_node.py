from typing import Optional

from pydantic import BaseModel, Field


class KnowledgeNode(BaseModel):
    id: Optional[str] = None
    student_id: Optional[str] = None
    material_id: str
    notebook_id: Optional[str] = None
    parent_id: Optional[str] = None
    title: str
    level: int = 1  # 1=章, 2=节（M2 先做到 1/2 即可）
    order: int = 0

    # 便于后续扩展：把材料 chunk 或摘要 chunk 关联到节点（M2 可不填）
    source_chunk_indexes: list[int] = Field(default_factory=list)
