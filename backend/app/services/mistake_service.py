from typing import Any, Dict, List, Optional

from app.db.mongo import get_db
from bson import ObjectId


def _mistakes_col():
    return get_db()["mistakes"]


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc


def list_mistakes(student_id: str, notebook_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {"student_id": student_id}
    if notebook_id:
        query["notebook_id"] = notebook_id
    docs = _mistakes_col().find(query).sort("wrong_count", -1)
    return [_serialize(doc) for doc in docs]
