from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.db.mongo import get_db


def _mastery_col(db):
    return db["mastery"]


def update_mastery_for_nodes(
    *,
    student_id: str,
    notebook_id: Optional[str],
    node_ids: List[str],
    is_correct: bool,
) -> None:
    if not student_id or not node_ids:
        return

    db = get_db()
    now = datetime.utcnow()

    for node_id in node_ids:
        q = {"student_id": student_id, "node_id": node_id}
        if notebook_id:
            q["notebook_id"] = notebook_id

        inc = {"seen": 1, "correct": 1 if is_correct else 0, "wrong": 0 if is_correct else 1}
        _mastery_col(db).update_one(
            q,
            {"$inc": inc, "$set": {"updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

        doc = _mastery_col(db).find_one(q, {"seen": 1, "correct": 1})
        seen = int((doc or {}).get("seen", 0) or 0)
        correct = int((doc or {}).get("correct", 0) or 0)
        score = (correct / seen) if seen > 0 else 0.0
        _mastery_col(db).update_one(q, {"$set": {"mastery_score": float(score)}})
