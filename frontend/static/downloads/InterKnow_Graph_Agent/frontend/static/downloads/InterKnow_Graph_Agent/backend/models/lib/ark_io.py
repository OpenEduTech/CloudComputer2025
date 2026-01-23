from __future__ import annotations
from typing import Any, Dict, Optional

def extract_text_from_ark_response(resp: Any) -> str:
    """
    兼容不同 Ark SDK / 返回对象形态，尽量拿到模型输出文本。
    """
    for attr in ("output_text", "text"):
        if hasattr(resp, attr):
            val = getattr(resp, attr)
            if isinstance(val, str) and val.strip():
                return val.strip()

    output = getattr(resp, "output", None)
    if isinstance(output, list):
        texts = []
        for item in output:
            content = getattr(item, "content", None)
            if content is None and isinstance(item, dict):
                content = item.get("content")

            if isinstance(content, list):
                for c in content:
                    t = getattr(c, "text", None)
                    if t is None and isinstance(c, dict):
                        t = c.get("text")
                    if isinstance(t, str) and t.strip():
                        texts.append(t.strip())

            t2 = getattr(item, "text", None)
            if isinstance(t2, str) and t2.strip():
                texts.append(t2.strip())

        if texts:
            return "\n".join(texts).strip()

    return str(resp).strip()

def extract_token_detail(resp: Any) -> Dict[str, int]:
    """
    尽量从响应里拿到 token usage。
    返回：{"prompt_tokens": x, "completion_tokens": y, "total_tokens": z}
    拿不到就返回全0。
    """
    usage = None
    if hasattr(resp, "usage"):
        usage = getattr(resp, "usage")
    elif isinstance(resp, dict):
        usage = resp.get("usage")

    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # usage 可能是对象，也可能是 dict
    def _get(u: Any, key: str) -> Optional[int]:
        if isinstance(u, dict):
            v = u.get(key)
            return int(v) if isinstance(v, (int, float)) else None
        if hasattr(u, key):
            v = getattr(u, key)
            return int(v) if isinstance(v, (int, float)) else None
        return None

    prompt_tokens = _get(usage, "prompt_tokens") or _get(usage, "input_tokens") or 0
    completion_tokens = _get(usage, "completion_tokens") or _get(usage, "output_tokens") or 0
    total_tokens = _get(usage, "total_tokens") or (prompt_tokens + completion_tokens)

    return {
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "total_tokens": int(total_tokens),
    }

def extract_total_tokens(resp: Any) -> int:
    return int(extract_token_detail(resp).get("total_tokens", 0))