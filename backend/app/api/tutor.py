"""Tutor API (M3): guided hint-ladder dialogue as a controlled state machine.

Only 2 endpoints are exposed:
- POST /tutor/start : create a session
- POST /tutor/next  : advance one turn (one question + one hint)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from bson.errors import InvalidId
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.tutor_service import (
    append_tutor_turn,
    create_tutor_session,
    get_tutor_session,
    suggest_next_level,
)
from app.tutor_runtime.engine import run_tutor_turn
from app.db.mongo import get_db


router = APIRouter()


def _strip_choice_label(text: str) -> str:
    s = str(text or "").strip()
    if len(s) >= 2 and s[0].upper() in "ABCDE" and s[1] in {".", "、", ":", "：", " "}:
        return s[2:].strip()
    return s


def _normalize_options(options: List[str]) -> List[str]:
    return [_strip_choice_label(opt) for opt in (options or [])]


class TutorStartRequest(BaseModel):
    student_id: str = Field(..., description="student_id")
    question_id: Optional[str] = Field(None, description="question_id (optional)")
    stem: str = Field(..., description="question stem")
    correct_answer: Optional[str] = Field(None, description="correct answer (stored server-side; not required)")
    student_answer: str = Field(..., description="student answer")
    question_type: Optional[str] = Field(None, description="question type (mcq/blank/short)")
    options: List[str] = Field(default_factory=list, description="mcq options")
    knowledge_points: List[str] = Field(default_factory=list, description="knowledge points")
    reference_analysis: Optional[str] = Field(None, description="reference analysis")

    missing_points: List[str] = Field(default_factory=list)
    error_tags: List[str] = Field(default_factory=list)
    weak_node_ids: List[str] = Field(default_factory=list)

    hint_level: str = Field("L0", description="initial level: L0/L1/L2")


class TutorStartResponse(BaseModel):
    session_id: str
    hint_level: str
    turn: int


@router.post("/start", response_model=TutorStartResponse)
def start_tutor(payload: TutorStartRequest):
    # Basic validation
    if not payload.student_id:
        raise HTTPException(status_code=400, detail="student_id is required")
    if not (payload.stem or "").strip():
        raise HTTPException(status_code=400, detail="stem is required")
    if not (payload.student_answer or "").strip():
        raise HTTPException(status_code=400, detail="student_answer is required")

    correct_answer = payload.correct_answer
    question_type = payload.question_type
    options = payload.options or []
    knowledge_points = payload.knowledge_points or []
    reference_analysis = payload.reference_analysis
    # If correct_answer not provided, try to fetch from questions collection by question_id
    if (not correct_answer) and payload.question_id:
        try:
            qdoc = get_db()["questions"].find_one({"_id": ObjectId(payload.question_id)})
            if qdoc:
                if not question_type and qdoc.get("type"):
                    question_type = str(qdoc.get("type"))
                if not options and qdoc.get("options"):
                    options = list(qdoc.get("options") or [])
                if not knowledge_points and qdoc.get("knowledge_points"):
                    knowledge_points = list(qdoc.get("knowledge_points") or [])
                if not reference_analysis and qdoc.get("analysis"):
                    reference_analysis = str(qdoc.get("analysis"))
                if (not correct_answer) and qdoc.get("answer_key"):
                    correct_answer = str(qdoc.get("answer_key"))
        except Exception:
            # silently ignore lookup failures; tutor will operate without anchor
            pass

    options = _normalize_options(options)

    # Resolve MCQ answer_key -> option text for better tutor grounding
    if question_type == "mcq" and options and correct_answer:
        letter = str(correct_answer).strip().upper()
        if len(letter) == 1 and "A" <= letter <= "Z":
            idx = ord(letter) - ord("A")
            if 0 <= idx < len(options):
                correct_answer = str(options[idx])
    session = create_tutor_session(
        student_id=payload.student_id,
        question_id=payload.question_id,
        stem=payload.stem,
        correct_answer=correct_answer,
        student_answer=payload.student_answer,
        question_type=question_type,
        options=options,
        knowledge_points=knowledge_points,
        reference_analysis=reference_analysis,
        missing_points=payload.missing_points,
        error_tags=payload.error_tags,
        weak_node_ids=payload.weak_node_ids,
        hint_level=payload.hint_level,
    )
    return {"session_id": session["id"], "hint_level": session["hint_level"], "turn": session["turn"]}


class TutorNextRequest(BaseModel):
    session_id: str
    message: str = Field("", description="student message for this turn")
    give_up: bool = Field(False, description="if true, allow FINAL answer")


@router.post("/next")
def next_tutor(payload: TutorNextRequest):
    if not payload.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    try:
        session = get_tutor_session(payload.session_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="invalid session_id")
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    # Update state machine
    next_level = suggest_next_level(
        current_level=session.get("hint_level", "L0"),
        turn=int(session.get("turn", 0) or 0),
        message=payload.message or "",
        give_up=bool(payload.give_up),
    )

    result = run_tutor_turn(session=session, message=payload.message or "", hint_level=next_level)

    # Persist
    append_tutor_turn(session_id=payload.session_id, user_message=payload.message or "", assistant_payload=result)

    # Return latest assistant payload
    return {"session_id": payload.session_id, "hint_level": next_level, "turn": session.get("turn", 0) + 1, "assistant": result}
