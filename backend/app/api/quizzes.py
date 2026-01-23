from typing import List, Optional

from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.jobs.queue import queue
from app.services.material_service import get_material
from app.services.quiz_service import create_quiz, get_quiz, list_questions

router = APIRouter()


class QuizGenerateRequest(BaseModel):
    student_id: str = "demo_user"
    notebook_id: str
    material_ids: List[str]
    num_questions: int = 5

    # M2：按知识点/章节出题（可选）
    node_id: Optional[str] = None

    difficulty: Optional[str] = None
    question_types: Optional[List[str]] = None
    type_mix: Optional[dict] = None
    difficulty_mix: Optional[dict] = None


class QuizGenerateResponse(BaseModel):
    id: str
    status: str
    job_id: str


@router.post("/generate", response_model=QuizGenerateResponse)
def generate_quiz(payload: QuizGenerateRequest):
    if not payload.material_ids:
        raise HTTPException(status_code=400, detail="material_ids is required")
    if payload.num_questions < 1 or payload.num_questions > 5:
        raise HTTPException(status_code=400, detail="num_questions must be between 1 and 5")
    if not payload.student_id:
        raise HTTPException(status_code=400, detail="student_id is required")

    for material_id in payload.material_ids:
        try:
            material = get_material(material_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail=f"invalid material_id: {material_id}")
        if not material:
            raise HTTPException(status_code=400, detail=f"material not found: {material_id}")
        if material.get("notebook_id") != payload.notebook_id:
            raise HTTPException(status_code=400, detail=f"material {material_id} not in this notebook")
        material_student = material.get("student_id")
        if material_student and material_student != payload.student_id:
            raise HTTPException(status_code=403, detail="material does not belong to this student")
        if not material_student and payload.student_id != "demo_user":
            raise HTTPException(status_code=403, detail="material belongs to default user")

    type_mix = payload.type_mix or _build_type_mix(payload.question_types)
    difficulty_mix = payload.difficulty_mix or _build_difficulty_mix(payload.difficulty)

    data = payload.dict()
    data["type_mix"] = type_mix
    data["difficulty_mix"] = difficulty_mix
    data.pop("question_types", None)
    data.pop("difficulty", None)

    quiz = create_quiz(data)
    job = queue.enqueue("tasks.generate_quiz.generate_quiz", quiz["id"])
    return {"id": quiz["id"], "status": "queued", "job_id": job.id}


@router.get("/{quiz_id}")
def get_quiz_detail(quiz_id: str):
    try:
        quiz = get_quiz(quiz_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="invalid quiz_id")
    if not quiz:
        raise HTTPException(status_code=404, detail="quiz not found")
    questions = list_questions(quiz_id)
    return {"quiz": quiz, "questions": questions}


def _build_type_mix(question_types: Optional[List[str]]) -> Optional[dict]:
    if not question_types:
        return None
    alias = {
        "选择": "mcq",
        "单选": "mcq",
        "choice": "mcq",
        "mcq": "mcq",
        "填空": "blank",
        "blank": "blank",
        "问答": "short",
        "简答": "short",
        "qa": "short",
        "short": "short",
    }
    normalized: List[str] = []
    for raw in question_types:
        key = str(raw).strip()
        if not key:
            continue
        mapped = alias.get(key) or alias.get(key.lower())
        if not mapped:
            raise HTTPException(status_code=400, detail=f"unsupported question_type: {raw}")
        if mapped not in normalized:
            normalized.append(mapped)
    if not normalized:
        return None
    share = 1.0 / len(normalized)
    mix = {t: share for t in normalized}
    if len(normalized) > 1:
        mix[normalized[-1]] = 1.0 - share * (len(normalized) - 1)
    return mix


def _build_difficulty_mix(difficulty: Optional[str]) -> Optional[dict]:
    if not difficulty:
        return None
    alias = {
        "简单": "L1",
        "容易": "L1",
        "easy": "L1",
        "l1": "L1",
        "L1": "L1",
        "正常": "L2",
        "中等": "L2",
        "normal": "L2",
        "l2": "L2",
        "L2": "L2",
        "难": "L3",
        "困难": "L3",
        "hard": "L3",
        "l3": "L3",
        "L3": "L3",
    }
    key = str(difficulty).strip()
    mapped = alias.get(key) or alias.get(key.lower())
    if not mapped:
        raise HTTPException(status_code=400, detail=f"unsupported difficulty: {difficulty}")
    return {mapped: 1.0}
