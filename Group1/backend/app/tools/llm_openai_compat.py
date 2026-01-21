from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings


def get_client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)


def _extract_json(text: str) -> dict[str, Any]:
    """
    Robust-ish JSON extraction for "JSON only" responses.
    """
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # fallback: take the first {...last}
    i = text.find("{")
    j = text.rfind("}")
    if i >= 0 and j > i:
        chunk = text[i : j + 1]
        obj = json.loads(chunk)
        if isinstance(obj, dict):
            return obj
    raise ValueError("Failed to parse JSON from LLM output")


def json_fix(graph_dict: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    """
    Ask the LLM to repair graph JSON according to schema constraints.
    Output must be a JSON object only.
    """
    client = get_client()
    model = settings.openai_model

    system = (
        "You are a strict JSON repair assistant. "
        "Return ONLY a valid JSON object, no markdown, no commentary."
    )
    user = {
        "task": "Fix the graph JSON to satisfy the schema and constraints.",
        "constraints": [
            "Keep concept/nodes/edges/meta structure.",
            "Each edge must have evidence.title and evidence.snippet (url optional).",
            "Edge.relation must be one of: related_to, used_in, is_a, explains, bridges.",
            "confidence must be within [0,1].",
            "checked must be boolean.",
            "Add missing fields with safe defaults; do not delete nodes/edges unless absolutely necessary.",
        ],
        "schema_errors": errors[:30],
        "graph": graph_dict,
    }

    # Prefer response_format if provider supports it; otherwise it will be ignored safely on many compat providers.
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},  # type: ignore[arg-type]
    )

    content = (resp.choices[0].message.content or "").strip()
    return _extract_json(content)

