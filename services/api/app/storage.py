import os
import json
import uuid
from typing import Any, Dict, List, Optional

import redis
from pymongo import MongoClient
from pymongo.collection import Collection

from datetime import datetime

from .models import MaterialCreate, MaterialUpdate, MemoryCreate, MemoryUpdate, Quiz


class DataStore:
    def __init__(self) -> None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        mongo_db = os.getenv("MONGO_DB", "learning_agent")
        self.mongo_client = MongoClient(mongo_uri)
        db = self.mongo_client[mongo_db]
        self.materials: Collection = db.materials
        self.quizzes: Collection = db.quizzes
        self.weaknesses: Collection = db.weaknesses
        self.memories: Collection = db.memories
        self.submissions: Collection = db.submissions
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def _sanitize_for_storage(value: Any) -> Any:
        if isinstance(value, str):
            return value.encode("utf-8", "ignore").decode("utf-8", "ignore")
        if isinstance(value, list):
            return [DataStore._sanitize_for_storage(item) for item in value]
        if isinstance(value, dict):
            return {k: DataStore._sanitize_for_storage(v) for k, v in value.items()}
        return value

    def save_material(self, material: MaterialCreate) -> str:
        doc = self._sanitize_for_storage(material.dict())
        doc["material_id"] = str(uuid.uuid4())
        doc.pop("memory_title", None)
        doc.pop("memory_content", None)
        doc.pop("memory_tags", None)
        self.materials.insert_one(doc)
        return doc["material_id"]

    def list_materials(self, user_id: str, topic: Optional[str], keyword: Optional[str]) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"user_id": user_id}
        if topic:
            query["topic"] = topic
        if keyword:
            query["content"] = {"$regex": keyword, "$options": "i"}
        docs = list(self.materials.find(query))
        for d in docs:
            d.pop("_id", None)
            d.pop("memory_title", None)
            d.pop("memory_content", None)
            d.pop("memory_tags", None)
        return docs

    def update_material(self, user_id: str, material_id: str, payload: MaterialUpdate) -> bool:
        query = {"user_id": user_id, "material_id": material_id}
        existing = self.materials.find_one(query)
        if not existing:
            return False
        patch = {k: self._sanitize_for_storage(v) for k, v in payload.dict().items() if v is not None}
        if not patch:
            return True  # allow idempotent save even when nothing changed
        res = self.materials.update_one(query, {"$set": patch})
        return res.matched_count > 0

    def delete_material(self, user_id: str, material_id: str) -> bool:
        res = self.materials.delete_one({"user_id": user_id, "material_id": material_id})
        return res.deleted_count > 0

    def save_quiz(self, quiz: Quiz) -> None:
        doc = quiz.dict()
        mongo_doc = self._sanitize_for_storage(dict(doc))
        self.quizzes.insert_one(mongo_doc)
        cache_doc = dict(mongo_doc)
        cache_doc.pop("_id", None)
        self.redis.set(f"quiz:{quiz.quiz_id}", json.dumps(cache_doc))

    def get_quiz(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        cached = self.redis.get(f"quiz:{quiz_id}")
        if cached:
            return json.loads(cached)
        doc = self.quizzes.find_one({"quiz_id": quiz_id})
        if doc:
            doc.pop("_id", None)
            self.redis.set(f"quiz:{quiz_id}", json.dumps(doc))
        return doc

    def upsert_weakness(self, user_id: str, entry: Dict[str, Any]) -> None:
        clean_entry = self._sanitize_for_storage(entry)
        self.weaknesses.update_one(
            {"user_id": user_id, "question_id": entry["question_id"]},
            {"$set": clean_entry},
            upsert=True,
        )

    def list_weaknesses(self, user_id: str) -> List[Dict[str, Any]]:
        docs = list(self.weaknesses.find({"user_id": user_id}))
        for d in docs:
            d.pop("_id", None)
        return docs

    def remove_weakness(self, user_id: str, question_id: str) -> bool:
        res = self.weaknesses.delete_one({"user_id": user_id, "question_id": question_id})
        return res.deleted_count > 0

    # Memories CRUD
    def create_memory(self, payload: MemoryCreate) -> str:
        doc = self._sanitize_for_storage(payload.dict())
        doc["memory_id"] = str(uuid.uuid4())
        self.memories.insert_one(doc)
        return doc["memory_id"]

    def list_memories(self, user_id: str, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"user_id": user_id}
        if keyword:
            regex = {"$regex": keyword, "$options": "i"}
            query["$or"] = [{"title": regex}, {"content": regex}, {"tags": regex}]
        docs = list(self.memories.find(query))
        for d in docs:
            d.pop("_id", None)
        return docs

    def update_memory(self, user_id: str, memory_id: str, patch: MemoryUpdate) -> bool:
        update_doc = {k: self._sanitize_for_storage(v) for k, v in patch.dict().items() if v is not None}
        if not update_doc:
            return False
        res = self.memories.update_one({"user_id": user_id, "memory_id": memory_id}, {"$set": update_doc})
        return res.matched_count > 0

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        res = self.memories.delete_one({"user_id": user_id, "memory_id": memory_id})
        return res.deleted_count > 0

    # Submissions / history
    def save_submission(self, submission: Dict[str, Any]) -> None:
        sanitized = self._sanitize_for_storage(submission)
        self.submissions.insert_one(sanitized)

    def list_submissions(self, user_id: str) -> List[Dict[str, Any]]:
        docs = list(self.submissions.find({"user_id": user_id}).sort("created_at", -1))
        for d in docs:
            d.pop("_id", None)
        return docs

    def get_submission(self, user_id: str, quiz_id: str) -> Optional[Dict[str, Any]]:
        doc = self.submissions.find_one({"user_id": user_id, "quiz_id": quiz_id}, sort=[("created_at", -1)])
        if doc:
            doc.pop("_id", None)
        return doc
