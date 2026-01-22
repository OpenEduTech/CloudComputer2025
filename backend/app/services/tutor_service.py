from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.db.mongo import get_db


def _col(db):
    return db["tutor_sessions"]


def create_tutor_session(
    student_id: str,
    question_id: Optional[str],
    stem: str,
    correct_answer: Optional[str],
    student_answer: str,
    question_type: Optional[str],
    options: Optional[List[str]],
    knowledge_points: List[str],
    reference_analysis: Optional[str],
    missing_points: List[str],
    error_tags: List[str],
    weak_node_ids: List[str],
    hint_level: str = "L0",
) -> Dict[str, Any]:
    db = get_db()
    now = datetime.utcnow()

    doc: Dict[str, Any] = {
        "student_id": student_id,
        "question_id": question_id,
        "stem": stem,
        "correct_answer": correct_answer,
        "student_answer": student_answer,
        "question": {
            "type": question_type,
            "options": options or [],
            "knowledge_points": knowledge_points or [],
            "reference_analysis": reference_analysis or "",
        },
        "diagnosis": {
            "missing_points": missing_points or [],
            "error_tags": error_tags or [],
            "weak_node_ids": weak_node_ids or [],
        },
        "hint_level": (hint_level or "L0").upper(),
        "turn": 0,
        "history": [],
        "created_at": now,
        "updated_at": now,
        "latest": None,
    }

    res = _col(db).insert_one(doc)
    return {"id": str(res.inserted_id), "hint_level": doc["hint_level"], "turn": 0}


def get_tutor_session(session_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    oid = ObjectId(session_id)
    doc = _col(db).find_one({"_id": oid})
    if not doc:
        return None
    doc["id"] = str(doc.pop("_id"))
    return doc


def append_tutor_turn(session_id: str, user_message: str, assistant_payload: Dict[str, Any]) -> None:
    db = get_db()
    oid = ObjectId(session_id)
    now = datetime.utcnow()

    # Keep last 10 entries in history (user/assistant pairs => up to 20 messages)
    history_updates = []
    if (user_message or "").strip():
        history_updates.append({"role": "user", "content": user_message, "created_at": now})
    history_updates.append({"role": "assistant", "content": assistant_payload, "created_at": now})

    _col(db).update_one(
        {"_id": oid},
        {
            "$push": {"history": {"$each": history_updates, "$slice": -20}},
            "$set": {
                "latest": assistant_payload,
                "hint_level": str(assistant_payload.get("hint_level") or "").upper() or None,
                "updated_at": now,
            },
            "$inc": {"turn": 1},
        },
    )


def suggest_next_level(current_level: str, turn: int, message: str, give_up: bool) -> str:
    """Controlled state machine for tutor hint level.

    Rules:
    - give_up=True or message includes 放弃/不会 -> FINAL
    - turn >= 6 -> FINAL
    - otherwise, promote level conservatively based on confusion cues
    """

    lvl = (current_level or "L0").upper()
    msg = (message or "").strip()

    if give_up or any(k in msg for k in ["放弃", "给答案", "直接告诉我", "不会", "不懂", "不知道"]):
        if turn >= 1:  # allow at least one attempt
            return "FINAL"

    if turn >= 6:
        return "FINAL"

    order = ["L0", "L1", "L2"]
    if lvl not in order:
        lvl = "L0"

    # If the student asks for a hint or is stuck, promote one level.
    if any(k in msg for k in ["提示", "怎么做", "求解", "下一步", "卡住"]):
        idx = order.index(lvl)
        return order[min(idx + 1, len(order) - 1)]

    return lvl
