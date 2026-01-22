from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId

class MaterialBase(BaseModel):
    filename: str
    user_id: Optional[str] = None

class MaterialCreate(MaterialBase):
    pass

class MaterialInDB(MaterialBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    content: Optional[str] = None # Parsed text content
    status: str = "pending" # pending, processing, completed, failed
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class MaterialResponse(MaterialInDB):
    pass
