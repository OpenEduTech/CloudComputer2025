from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services.mistake_service import list_mistakes

router = APIRouter()


@router.get("/")
def list_mistakes_api(student_id: Optional[str] = None, notebook_id: Optional[str] = None):
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")
    if not notebook_id:
        raise HTTPException(status_code=400, detail="notebook_id is required")
    return {"mistakes": list_mistakes(student_id, notebook_id)}
