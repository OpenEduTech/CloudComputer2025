import json
from datetime import datetime

import redis

from app.core.config import settings


def _get_client() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def save_questions(session_id: str, questions: list[dict]) -> None:
    """
    保存题目列表（覆盖式）。
    """
    client = _get_client()
    key = f"questions:{session_id}"
    payload = {
        "session_id": session_id,
        "updated_at": datetime.utcnow().isoformat(),
        "questions": questions,
    }
    client.set(key, json.dumps(payload, ensure_ascii=False))


def save_answers(session_id: str, answers: list[dict]) -> None:
    """
    保存最近一次作答。
    """
    client = _get_client()
    key = f"answers:{session_id}:latest"
    payload = {
        "session_id": session_id,
        "updated_at": datetime.utcnow().isoformat(),
        "answers": answers,
    }
    client.set(key, json.dumps(payload, ensure_ascii=False))


def load_latest_record(session_id: str) -> dict:
    """
    读取最近一次题目与作答。
    """
    client = _get_client()
    q_raw = client.get(f"questions:{session_id}")
    a_raw = client.get(f"answers:{session_id}:latest")
    result = {"session_id": session_id, "questions": [], "answers": []}
    if q_raw:
        try:
            result["questions"] = json.loads(q_raw).get("questions", [])
        except json.JSONDecodeError:
            pass
    if a_raw:
        try:
            result["answers"] = json.loads(a_raw).get("answers", [])
        except json.JSONDecodeError:
            pass
    return result
