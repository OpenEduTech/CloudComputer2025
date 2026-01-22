from typing import Optional

from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.jobs.queue import queue
from app.services.coach_service import get_latest_coach_plan


router = APIRouter()


class CoachGenerateRequest(BaseModel):
    """Request to generate a coaching plan.

    - notebook_id is recommended so we can scope to a course.
    - material_id is optional (for scoping to a specific material).
    """

    student_id: str = Field(..., description="student_id")
    notebook_id: Optional[str] = Field(None, description="notebook_id")
    material_id: Optional[str] = Field(None, description="material_id")
    days: int = Field(14, ge=1, le=120, description="lookback days")
    top_k: int = Field(5, ge=1, le=20, description="top K mistakes")


@router.post("/generate")
def generate_coach(payload: CoachGenerateRequest):
    """Enqueue a background job to generate a coaching plan."""

    if not payload.student_id:
        raise HTTPException(status_code=400, detail="student_id is required")

    job = queue.enqueue(
        "tasks.coach.generate_coach",
        payload.student_id,
        payload.notebook_id,
        payload.material_id,
        payload.days,
        payload.top_k,
    )
    return {"status": "queued", "job_id": job.id}


@router.get("/latest")
def get_latest(student_id: Optional[str] = None, notebook_id: Optional[str] = None, material_id: Optional[str] = None):
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")
    try:
        plan = get_latest_coach_plan(student_id=student_id, notebook_id=notebook_id, material_id=material_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="invalid id")
    if not plan:
        return {"plan": None}
    return {"plan": plan}
