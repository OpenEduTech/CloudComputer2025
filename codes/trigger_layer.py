from __future__ import annotations

import json
from typing import Any, Dict

from orchestrator import run_pipeline
from config import DEFAULT_KEYWORD


def handler(event: Any, context: Any) -> Dict[str, Any]:
    """阿里云 FC 的入口函数（兼容定时触发器 payload）。

    event 可能是 bytes / str（来自触发器 payload），也可能已是 dict。
    """
    keyword = DEFAULT_KEYWORD

    try:
        if isinstance(event, (bytes, bytearray)):
            evt = json.loads(event.decode("utf-8") or "{}")
        elif isinstance(event, str):
            evt = json.loads(event or "{}")
        elif isinstance(event, dict):
            evt = event
        else:
            evt = {}
        keyword = evt.get("keyword", DEFAULT_KEYWORD)
    except Exception:
        evt = {}
        keyword = DEFAULT_KEYWORD

    # 调用已有编排逻辑
    result = run_pipeline(keyword=keyword, print_steps=False)

    decisions = result.get("decisions", [])
    raw_changes_count = int(result.get("raw_changes_count", 0) or 0)

    summary = {
        "keyword": keyword,
        "raw_changes_count": raw_changes_count,
        "decisions_count": len(decisions),
    }

    return {
        "status": "success",
        "global_summary": summary,
        "raw_changes_count": summary["raw_changes_count"],
    }
