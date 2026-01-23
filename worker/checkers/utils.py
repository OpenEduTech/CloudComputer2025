from __future__ import annotations

import json
import re
from typing import Any, Tuple


_CODE_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n(?P<body>[\s\S]*?)\n```\s*$")


def strip_code_fence(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    m = _CODE_FENCE_RE.match(text.strip())
    if m:
        return (m.group("body") or "").strip()
    return text.strip()


def safe_json_loads(text: str) -> Tuple[bool, Any, str]:
    """Parse JSON safely.

    Returns (ok, obj, error_message)
    """
    cleaned = strip_code_fence(text)
    try:
        return True, json.loads(cleaned), ""
    except Exception as e:
        return False, None, f"json parse error: {e}"
