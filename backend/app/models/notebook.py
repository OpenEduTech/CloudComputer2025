from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Notebook(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    owner_id: Optional[str] = None
    created_at: Optional[datetime] = None
