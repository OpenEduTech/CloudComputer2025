import json
from datetime import datetime

import redis

from app.core.config import settings


def _get_client() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def save_wrong_items(session_id: str, items: list[dict]) -> int:
    """
    将错题写入 Redis，返回写入条目数。
    """
    client = _get_client()
    key = f"wrongbook:{session_id}"
    now = datetime.utcnow().isoformat()
    payload = []
    for item in items:
        item["timestamp"] = now
        payload.append(json.dumps(item, ensure_ascii=False))
    if payload:
        client.rpush(key, *payload)
    return len(payload)


def load_wrong_items(session_id: str) -> list[dict]:
    """
    读取错题列表。
    """
    client = _get_client()
    key = f"wrongbook:{session_id}"
    raw = client.lrange(key, 0, -1)
    result = []
    for r in raw:
        try:
            result.append(json.loads(r))
        except json.JSONDecodeError:
            continue
    return result


def summarize_wrong_items(items: list[dict]) -> dict:
    """
    简单统计错题情况：按题型关键词计数。
    """
    summary = {
        "total": len(items),
        "by_keyword": {}
    }
    for item in items:
        text = item.get("question", "")
        # 简单关键词统计
        for key in ["感知机", "收敛", "损失函数", "超平面", "更新"]:
            if key in text:
                summary["by_keyword"][key] = summary["by_keyword"].get(key, 0) + 1
    return summary
