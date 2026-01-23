from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from app.db.mongo import get_db


def _quizzes_col():
    return get_db()["quizzes"]


def _questions_col():
    return get_db()["questions"]


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc


def create_quiz(payload: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    doc = {
        "student_id": payload.get("student_id", "demo_user"),
        "notebook_id": payload["notebook_id"],
        "material_ids": payload["material_ids"],
        "status": "generating",
        "question_ids": [],
        "num_questions": payload.get("num_questions", 5),
        "type_mix": payload.get("type_mix"),
        "difficulty_mix": payload.get("difficulty_mix"),
        # === M2：按知识点/章节范围出题（可选）===
        # 统一字段名：node_id
        "node_id": payload.get("node_id"),
        "created_at": now,
    }
    result = _quizzes_col().insert_one(doc)
    return {"id": str(result.inserted_id), "status": doc["status"]}


def get_quiz(quiz_id: str) -> Optional[Dict[str, Any]]:
    doc = _quizzes_col().find_one({"_id": ObjectId(quiz_id)})
    if not doc:
        return None
    return _serialize(doc)


def update_quiz(
    quiz_id: str,
    status: Optional[str] = None,
    question_ids: Optional[List[str]] = None,
    error_message: Optional[str] = None,
) -> None:
    updates: Dict[str, Any] = {}
    if status:
        updates["status"] = status
    if question_ids is not None:
        updates["question_ids"] = question_ids
    if error_message:
        updates["error_message"] = error_message
    if updates:
        _quizzes_col().update_one({"_id": ObjectId(quiz_id)}, {"$set": updates})


def list_questions(quiz_id: str) -> List[Dict[str, Any]]:
    docs = _questions_col().find({"quiz_id": quiz_id})
    return [_serialize(doc) for doc in docs]
