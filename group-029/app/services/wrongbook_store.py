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
    # 重建列表，保证删除后数据一致
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
    keywords = ["定义", "公式", "步骤", "条件", "推导", "性质", "应用", "对比", "示例", "误区"]
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
        "定义": "优先复习核心概念的定义、术语含义与适用范围。",
        "公式": "梳理关键公式的来源与符号含义，确保能正确代入与推导。",
        "步骤": "复盘算法或流程步骤，明确每一步的输入输出与作用。",
        "条件": "关注成立条件与前提假设，避免在不适用场景中误用结论。",
        "推导": "补齐推导链路，理解公式或结论如何得到。",
        "性质": "总结关键性质与特点，并与相似概念区分。",
        "应用": "结合典型应用场景或例题，验证理解是否到位。",
        "对比": "列出易混概念差异点，避免混淆。",
        "示例": "通过代表性例子回顾概念与公式的具体用法。",
        "误区": "针对常见错误点做专项纠偏，标注易错原因。",
    }
    suggestions = [mapping.get(k, f"复习与“{k}”相关的定义、性质与应用场景。") for k in top]
    return " ".join(suggestions)
