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
    mutated = False
    for r in raw:
        try:
            item = json.loads(r)
        except json.JSONDecodeError:
            continue
        if not item.get("record_id"):
            item["record_id"] = uuid4().hex
            mutated = True
        result.append(item)
    if mutated:
        client.delete(key)
        payload = [json.dumps(i, ensure_ascii=False) for i in result]
        if payload:
            client.rpush(key, *payload)
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
    keywords = ["感知机", "收敛", "损失函数", "超平面", "更新", "梯度", "判别", "线性可分"]
    for item in items:
        text = item.get("question", "")
        for key in keywords:
            if key in text:
                summary["by_keyword"][key] = summary["by_keyword"].get(key, 0) + 1
    return summary


def build_personal_suggestion(summary: dict) -> str:
    """
    根据错题关键词生成针对性小灶建议。
    """
    by_keyword = summary.get("by_keyword", {})
    if not by_keyword:
        return "当前无错题，建议尝试提高题量或选择更难的章节练习。"
    ordered = sorted(by_keyword.items(), key=lambda x: x[1], reverse=True)
    top = [k for k, _ in ordered[:3]]
    mapping = {
        "感知机": "重点回顾感知机模型定义、几何解释与更新规则。",
        "收敛": "复习收敛性定理的条件与证明思路，关注线性可分前提。",
        "损失函数": "梳理感知机损失函数推导与几何含义，比较几何距离与函数间隔。",
        "超平面": "巩固超平面方程与法向量含义，理解分类边界的移动。",
        "更新": "强化参数更新公式的来源与直观意义，结合梯度下降理解方向。",
        "梯度": "复习梯度下降的推导过程，掌握对 w 与 b 的偏导。",
        "判别": "理解判别模型与生成模型区别，掌握感知机的判别特性。",
        "线性可分": "强化线性可分的定义与例子，理解不可分时的局限。",
    }
    suggestions = [mapping.get(k, f"复习与“{k}”相关的定义、性质与应用场景。") for k in top]
    return " ".join(suggestions)
