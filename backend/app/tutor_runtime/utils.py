from __future__ import annotations

import datetime
import json
from typing import Any, Optional, Tuple

try:
    # bson is available when pymongo is installed
    from bson import ObjectId  # type: ignore
except Exception:  # pragma: no cover
    ObjectId = None  # type: ignore


def strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def safe_json_loads(text: str) -> Tuple[bool, Optional[Any], str]:
    """Best-effort JSON parse.

    Returns: (ok, obj, error_message)
    """

    raw = strip_code_fence(text)
    try:
        return True, json.loads(raw), ""
    except Exception as e:
        return False, None, f"invalid JSON: {e}"


def make_jsonable(obj: Any) -> Any:
    """Convert common non-JSON types (datetime, ObjectId, bytes, etc.) to JSON-safe values.

    This is mainly used to safely embed MongoDB documents into prompts.
    """

    # Fast paths
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # datetime/date -> ISO8601 string
    if isinstance(obj, (datetime.datetime, datetime.date)):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)

    # bson ObjectId -> str
    if ObjectId is not None and isinstance(obj, ObjectId):
        return str(obj)

    # bytes -> utf-8 (fallback to repr)
    if isinstance(obj, (bytes, bytearray)):
        try:
            return bytes(obj).decode("utf-8", errors="replace")
        except Exception:
            return repr(obj)

    # dict/list/tuple -> recurse
    if isinstance(obj, dict):
        return {str(k): make_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_jsonable(v) for v in obj]

    # Anything else -> best-effort string
    return str(obj)
