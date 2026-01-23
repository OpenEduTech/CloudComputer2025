from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MaterialText(BaseModel):
    id: Optional[str] = None
    material_id: str
    kind: str  # full/summary
    chunk_index: int
    text: str
    created_at: Optional[datetime] = None
