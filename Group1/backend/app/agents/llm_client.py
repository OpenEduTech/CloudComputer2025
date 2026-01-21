from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings


def get_openai_client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)


def extract_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    i = text.find("{")
    j = text.rfind("}")
    if i >= 0 and j > i:
        obj = json.loads(text[i : j + 1])
        if isinstance(obj, dict):
            return obj
    raise ValueError("Failed to parse JSON object from LLM output")


def chat_json(system: str, payload: dict[str, Any], *, model: str | None = None, temperature: float = 0.2) -> dict[str, Any]:
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=model or settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},  # type: ignore[arg-type]
    )
    content = (resp.choices[0].message.content or "").strip()
    return extract_json_object(content)

