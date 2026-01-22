from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.db.mongo import get_db


def _materials_col():
    return get_db()["materials"]


def _material_texts_col():
    return get_db()["material_texts"]


def _apply_student_filter(query: Dict[str, Any], student_id: Optional[str]) -> None:
    if not student_id:
        return
    if student_id == "demo_user":
        query["$or"] = [{"student_id": student_id}, {"student_id": {"$exists": False}}]
    else:
        query["student_id"] = student_id


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc


def _split_text(text: str, max_chars: int = 2000) -> List[str]:
    text = text.strip()
    if not text:
        return []
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def create_material(payload: Dict[str, Any], text: Optional[str] = None) -> Dict[str, Any]:
    now = datetime.utcnow()
    doc = {
        "student_id": payload.get("student_id", "demo_user"),
        "notebook_id": payload["notebook_id"],
        "title": payload["title"],
        "source_type": payload["source_type"],
        "material_type": payload["material_type"],
        "is_primary": bool(payload.get("is_primary", False)),
        "status": payload.get("status", "uploaded"),
        "file_url": payload.get("file_url"),
        "text_chunk_count": 0,
        "summary_chunk_count": 0,
        "created_at": now,
    }

    result = _materials_col().insert_one(doc)
    material_id = str(result.inserted_id)

    if text:
        chunks = _split_text(text)
        if chunks:
            insert_material_texts(
                material_id,
                chunks,
                kind="full",
                student_id=doc.get("student_id"),
                notebook_id=doc.get("notebook_id"),
            )
            _materials_col().update_one(
                {"_id": result.inserted_id},
                {"$set": {"text_chunk_count": len(chunks), "status": "ready"}},
            )
            doc["text_chunk_count"] = len(chunks)
            doc["status"] = "ready"

    if doc["is_primary"] and doc["material_type"] == "textbook":
        set_primary_material(doc["notebook_id"], doc.get("student_id"), material_id)

    return {"id": material_id, "status": doc["status"], "text_chunk_count": doc["text_chunk_count"]}


def insert_material_texts(
    material_id: str,
    chunks: List[str],
    kind: str,
    student_id: Optional[str] = None,
    notebook_id: Optional[str] = None,
) -> None:
    now = datetime.utcnow()
    docs = []
    for idx, chunk in enumerate(chunks):
        doc = {
            "material_id": material_id,
            "kind": kind,
            "chunk_index": idx,
            "text": chunk,
            "created_at": now,
        }
        if student_id:
            doc["student_id"] = student_id
        if notebook_id:
            doc["notebook_id"] = notebook_id
        docs.append(doc)
    if docs:
        _material_texts_col().insert_many(docs)


def get_material(material_id: str) -> Optional[Dict[str, Any]]:
    doc = _materials_col().find_one({"_id": ObjectId(material_id)})
    if not doc:
        return None
    return _serialize(doc)


def list_materials(notebook_id: str, student_id: Optional[str]) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {"notebook_id": notebook_id}
    _apply_student_filter(query, student_id)
    docs = _materials_col().find(query).sort("created_at", 1)
    return [_serialize(doc) for doc in docs]


def set_primary_material(notebook_id: str, student_id: Optional[str], material_id: str) -> None:
    query: Dict[str, Any] = {"notebook_id": notebook_id, "material_type": "textbook"}
    _apply_student_filter(query, student_id)
    _materials_col().update_many(
        query,
        {"$set": {"is_primary": False}},
    )
    _materials_col().update_one(
        {"_id": ObjectId(material_id)},
        {"$set": {"is_primary": True}},
    )


def update_material_status(
    material_id: str,
    status: str,
    text_chunk_count: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    updates: Dict[str, Any] = {"status": status}
    if text_chunk_count is not None:
        updates["text_chunk_count"] = text_chunk_count
    if error_message is not None:
        updates["error_message"] = error_message
    _materials_col().update_one({"_id": ObjectId(material_id)}, {"$set": updates})
