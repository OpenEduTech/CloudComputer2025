from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId

from app.db.mongo import get_db


def _attempts_col():
    return get_db()["attempts"]


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc


def create_attempt(quiz_id: str, student_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    doc = {
        "quiz_id": quiz_id,
        "student_id": student_id,
        "answers": answers,
        "status": "grading",
        "grading": None,
        "score": None,
        "created_at": now,
    }
    result = _attempts_col().insert_one(doc)
    return {"id": str(result.inserted_id), "status": doc["status"]}


def get_attempt(attempt_id: str) -> Optional[Dict[str, Any]]:
    doc = _attempts_col().find_one({"_id": ObjectId(attempt_id)})
    if not doc:
        return None
    return _serialize(doc)


def update_attempt(attempt_id: str, updates: Dict[str, Any]) -> None:
    if updates:
        _attempts_col().update_one({"_id": ObjectId(attempt_id)}, {"$set": updates})
