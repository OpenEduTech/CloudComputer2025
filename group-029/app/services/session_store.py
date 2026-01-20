import json
import os
from uuid import uuid4


DATA_DIR = "data"
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")


def _ensure_dirs():
    # 确保数据目录存在
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def create_session(chunks: list[dict]) -> str:
    _ensure_dirs()
    session_id = uuid4().hex
    session_path = os.path.join(SESSIONS_DIR, session_id)
    os.makedirs(session_path, exist_ok=True)
    with open(os.path.join(session_path, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    return session_id


def load_chunks(session_id: str) -> list[dict]:
    session_path = os.path.join(SESSIONS_DIR, session_id, "chunks.json")
    if not os.path.exists(session_path):
        return []
    with open(session_path, "r", encoding="utf-8") as f:
        return json.load(f)
