import json
import os
import shutil
from datetime import datetime
from uuid import uuid4


DATA_DIR = "data"
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")


def _ensure_dirs():
    # 确保数据目录存在
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def create_session(chunks: list[dict], name: str) -> str:
    _ensure_dirs()
    session_id = uuid4().hex
    session_path = os.path.join(SESSIONS_DIR, session_id)
    os.makedirs(session_path, exist_ok=True)
    with open(os.path.join(session_path, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    meta = {
        "session_id": session_id,
        "name": name,
        "created_at": datetime.utcnow().isoformat(),
        "last_accessed": datetime.utcnow().isoformat(),
        "chunk_count": len(chunks),
    }
    with open(os.path.join(session_path, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return session_id


def load_chunks(session_id: str) -> list[dict]:
    session_path = os.path.join(SESSIONS_DIR, session_id, "chunks.json")
    if not os.path.exists(session_path):
        return []
    with open(session_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_sessions() -> list[dict]:
    _ensure_dirs()
    results = []
    for name in os.listdir(SESSIONS_DIR):
        session_path = os.path.join(SESSIONS_DIR, name)
        meta_path = os.path.join(session_path, "meta.json")
        if not os.path.isdir(session_path):
            continue
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if "last_accessed" not in meta:
                meta["last_accessed"] = meta.get("created_at", datetime.utcnow().isoformat())
            results.append(meta)
        else:
            chunks_path = os.path.join(session_path, "chunks.json")
            if os.path.exists(chunks_path):
                with open(chunks_path, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
                created_at = datetime.utcfromtimestamp(
                    os.path.getmtime(chunks_path)
                ).isoformat()
                results.append(
                    {
                        "session_id": name,
                        "name": name,
                        "created_at": created_at,
                        "last_accessed": created_at,
                        "chunk_count": len(chunks),
                    }
                )
    # 最近访问排前面
    results.sort(key=lambda x: x.get("last_accessed", x.get("created_at", "")), reverse=True)
    return results


def delete_session(session_id: str) -> bool:
    session_path = os.path.join(SESSIONS_DIR, session_id)
    if not os.path.isdir(session_path):
        return False
    shutil.rmtree(session_path)
    return True


def update_session_name(session_id: str, new_name: str) -> bool:
    session_path = os.path.join(SESSIONS_DIR, session_id, "meta.json")
    if not os.path.exists(session_path):
        return False
    with open(session_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    meta["name"] = new_name
    meta["last_accessed"] = datetime.utcnow().isoformat()
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return True


def touch_session(session_id: str) -> None:
    session_path = os.path.join(SESSIONS_DIR, session_id, "meta.json")
    if not os.path.exists(session_path):
        return
    with open(session_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    meta["last_accessed"] = datetime.utcnow().isoformat()
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
