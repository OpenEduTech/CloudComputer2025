from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId

from app.db.mongo import get_db


def _coach_plans_col():
    return get_db()["coach_plans"]


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    # datetime -> iso
    for k in ("created_at", "updated_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    return doc


def get_latest_coach_plan(
    student_id: str,
    notebook_id: Optional[str] = None,
    material_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    query: Dict[str, Any] = {"student_id": student_id}
    if notebook_id:
        query["notebook_id"] = notebook_id
    if material_id:
        query["material_id"] = material_id

    doc = _coach_plans_col().find_one(query, sort=[("created_at", -1)])
    if not doc:
        return None
    return _serialize(doc)
