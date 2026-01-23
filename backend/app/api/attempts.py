from typing import Any, Dict

from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.jobs.queue import queue
from app.services.attempt_service import create_attempt, get_attempt
from app.services.quiz_service import get_quiz

router = APIRouter()


class AttemptCreateRequest(BaseModel):
    student_id: str = "demo_user"
    answers: Dict[str, Any]


class AttemptCreateResponse(BaseModel):
    id: str
    status: str
    job_id: str


@router.post("/{quiz_id}/submit", response_model=AttemptCreateResponse)
def submit_attempt(quiz_id: str, payload: AttemptCreateRequest):
    try:
        quiz = get_quiz(quiz_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="invalid quiz_id")
    if not quiz:
        raise HTTPException(status_code=404, detail="quiz not found")
    quiz_student = quiz.get("student_id")
    if quiz_student and quiz_student != payload.student_id:
        raise HTTPException(status_code=403, detail="quiz does not belong to this student")
    if not quiz_student and payload.student_id != "demo_user":
        raise HTTPException(status_code=403, detail="quiz belongs to default user")
    attempt = create_attempt(quiz_id, payload.student_id, payload.answers)
    job = queue.enqueue("tasks.grade_attempt.grade_attempt", attempt["id"])
    return {"id": attempt["id"], "status": attempt["status"], "job_id": job.id}


@router.get("/{attempt_id}")
def get_attempt_detail(attempt_id: str):
    try:
        attempt = get_attempt(attempt_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="invalid attempt_id")
    if not attempt:
        raise HTTPException(status_code=404, detail="attempt not found")
    return attempt
