import json
from datetime import datetime
from uuid import uuid4

import redis

from app.core.config import settings


def _get_client() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def save_wrong_items(session_id: str, items: list[dict]) -> int:
    """
    将错题写入 Redis，返回写入条目数。
    """
    client = _get_client()
    # 错题本为全局汇总，不与单一会话绑定
    key = "wrongbook:all"
    now = datetime.utcnow().isoformat()
    payload = []
    for item in items:
        item["record_id"] = item.get("record_id") or uuid4().hex
        item["timestamp"] = now
        item["session_id"] = session_id
        payload.append(json.dumps(item, ensure_ascii=False))
    if payload:
        client.rpush(key, *payload)
    return len(payload)


def load_wrong_items_all() -> list[dict]:
    """
    读取全局错题列表。
    """
    client = _get_client()
    key = "wrongbook:all"
    raw = client.lrange(key, 0, -1)
    result = []
    for r in raw:
        try:
            result.append(json.loads(r))
        except json.JSONDecodeError:
            continue
    return result


def delete_wrong_item(record_id: str) -> bool:
    """
    删除指定错题记录。
    """
    client = _get_client()
    key = "wrongbook:all"
    raw = client.lrange(key, 0, -1)
    kept = []
    deleted = False
    for r in raw:
        try:
            item = json.loads(r)
        except json.JSONDecodeError:
            continue
        if item.get("record_id") == record_id and not deleted:
            deleted = True
            continue
        kept.append(item)
    if not deleted:
        return False
    client.delete(key)
    if kept:
        payload = [json.dumps(i, ensure_ascii=False) for i in kept]
        client.rpush(key, *payload)
    return True


def summarize_wrong_items(items: list[dict]) -> dict:
    """
    简单统计错题情况：按关键词计数。
    """
    summary = {
        "total": len(items),
        "by_keyword": {},
    }
    keywords = ["感知机", "收敛", "损失函数", "超平面", "更新"]
    for item in items:
        text = item.get("question", "")
        for key in keywords:
            if key in text:
                summary["by_keyword"][key] = summary["by_keyword"].get(key, 0) + 1
    return summary
