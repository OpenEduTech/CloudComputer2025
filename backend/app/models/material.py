from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Material(BaseModel):
    id: Optional[str] = None
    student_id: str
    notebook_id: str
    title: str
    source_type: str  # text/pdf/docx/audio
    material_type: str  # textbook/note/handout/other
    is_primary: bool = False
    status: str = "uploaded"
    file_url: Optional[str] = None
    text_chunk_count: int = 0
    summary_chunk_count: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
