import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

KIMI_API_KEY = os.getenv("MOONSHOT_API_KEY")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def _call_kimi(prompt: str) -> str:
    if not KIMI_API_KEY:
        raise RuntimeError("MOONSHOT_API_KEY is required for quiz generation")
    client = OpenAI(api_key=KIMI_API_KEY, base_url="https://api.moonshot.cn/v1")
    resp = client.chat.completions.create(
        model=KIMI_MODEL,
        messages=[
            {"role": "system", "content": "You are a quiz generator. Output JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def _normalize_type(t: str) -> str:
    t = (t or "").strip().lower()
    alias = {
        "mcq": "mcq",
        "choice": "mcq",
        "single": "mcq",
        "blank": "blank",
        "fill": "blank",
        "short": "short",
        "qa": "short",
        "essay": "short",
    }
    return alias.get(t, t)


def _validate_questions(qs: Any) -> List[Dict[str, Any]]:
    if not isinstance(qs, list) or not qs:
        raise ValueError("questions must be a non-empty array")
    out: List[Dict[str, Any]] = []
    for q in qs:
        if not isinstance(q, dict):
            raise ValueError("each question must be object")
        qtype = _normalize_type(str(q.get("type", "mcq")))
        stem = str(q.get("stem", "")).strip()
        if not stem:
            raise ValueError("question stem is empty")

        difficulty = str(q.get("difficulty", "L2")).strip().upper()
        if difficulty not in ("L1", "L2", "L3"):
            difficulty = "L2"

        doc: Dict[str, Any] = {
            "type": qtype,
            "stem": stem,
            "difficulty": difficulty,
            "rubric": str(q.get("rubric", "")).strip(),
            "answer_key": q.get("answer_key", ""),
            "analysis": str(q.get("analysis", "")).strip(),
            "knowledge_points": q.get("knowledge_points") or [],
        }

        if qtype == "mcq":
            opts = q.get("options") or []
            if not isinstance(opts, list) or len(opts) < 2:
                raise ValueError("mcq options must be list with >=2 items")
            doc["options"] = [str(x) for x in opts]
            doc["answer_key"] = str(doc["answer_key"]).strip() or "A"
        else:
            doc["options"] = []

        out.append(doc)
    return out


def generate_quiz_from_text(text: str, payload: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    输入教材文本，输出结构化题目列表。
    payload 支持：
      - num_questions (1-5)
      - type_mix / difficulty_mix（可不严格实现；M2 先保证字段存在即可）
    """
    payload = payload or {}
    num_questions = int(payload.get("num_questions", 5))
    if num_questions < 1:
        num_questions = 1
    if num_questions > 5:
        num_questions = 5

    prompt = (
        "基于以下学习资料，生成测验题目。只输出 JSON 数组，不要输出任何解释。\n"
        "数组长度严格等于 num_questions。\n"
        "每个元素字段：\n"
        "- type: mcq/blank/short\n"
        "- stem: 题干\n"
        "- options: 仅当 type=mcq 时提供，形如 [\"A ...\",\"B ...\",...]\n"
        "- answer_key: mcq 填 \"A\"/\"B\"/...；blank/short 给参考答案文本\n"
        "- rubric: 简答/填空评分要点（mcq 可空）\n"
        "- difficulty: L1/L2/L3\n"
        "- knowledge_points: 字符串数组（2-5个）\n"
        "- analysis: 解析（不要太长）\n\n"
        f"num_questions={num_questions}\n\n"
        f"学习资料：\n{text}\n"
    )

    raw = _call_kimi(prompt)
    data = json.loads(_strip_code_fence(raw))
    return _validate_questions(data)
