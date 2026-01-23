from __future__ import annotations

import json
from typing import Any

from app.config import settings


def _mock_plan(concept: str, domains: list[str]) -> dict[str, list[str]]:
    c = concept.strip().lower()
    # Minimal curated rules to make demos strong offline.
    if "递归" in concept or "recursion" in c:
        base = {
            "Mathematics": ["递推关系 (recurrence relation)", "数学归纳法 (mathematical induction)", "斐波那契数列 (Fibonacci sequence)"],
            "Computer Science": ["递归函数 (recursive function)", "调用栈 (call stack)", "分治 (divide and conquer)"],
            "Physics": ["分形 (fractal)", "自相似 (self-similarity)", "尺度不变 (scale invariance)"],
            "Biology": ["反馈回路 (feedback loop)", "分支结构 (branching structures)", "层级组织 (hierarchical organization)"],
            "Economics": ["动态规划 (dynamic programming)", "Bellman 方程 (Bellman equation)", "递归效用 (recursive utility)"],
        }
    elif "熵" in concept or "entropy" in c:
        base = {
            "Mathematics": ["概率分布 (probability distribution)", "KL 散度 (KL divergence)", "互信息 (mutual information)"],
            "Physics": ["热力学第二定律 (second law)", "统计力学 (statistical mechanics)", "微观态 (microstate)"],
            "Computer Science": ["信息熵 (Shannon entropy)", "交叉熵 (cross-entropy)", "编码 (coding theory)"],
            "Biology": ["序列多样性 (sequence diversity)", "信息量 (information content)", "生态多样性 (diversity index)"],
            "Economics": ["不确定性 (uncertainty)", "信息不对称 (information asymmetry)", "多样性指标 (diversity measure)"],
        }
    else:
        # Generic plan: still force multi-domain outputs even if unknown
        base = {
            d: [
                f"{concept} in {d}",
                f"{concept} applications ({d})",
                f"{concept} related concepts ({d})",
            ]
            for d in domains
        }
    out: dict[str, list[str]] = {}
    for d in domains:
        out[d] = base.get(d, base.get("Computer Science", [concept]))  # type: ignore[arg-type]
    return out


def _extract_json(text: str) -> dict[str, Any]:
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
        return json.loads(text[i : j + 1])
    raise ValueError("Planner: failed to parse JSON")


def plan(concept: str, domains: list[str]) -> dict[str, list[str]]:
    """
    Return domain -> list of query concepts.
    - mock: offline heuristics
    - openai_compat: LLM forced JSON output
    """
    if settings.llm_provider != "openai_compat" or not settings.openai_api_key:
        return _mock_plan(concept, domains)

    # LLM plan
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    prompt = {
        "concept": concept,
        "domains": domains,
        "requirements": [
            "For EACH domain, output 3-6 related concepts/bridge concepts.",
            "The output must be a JSON object: {\"domains\": {\"Domain\": [\"concept1\", ...]}}",
            "Prefer concrete terms students can recognize (textbook keywords).",
            "Keep items short; can include bilingual hint in parentheses.",
        ],
    }
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "Return ONLY a JSON object. No markdown."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},  # type: ignore[arg-type]
    )
    content = (resp.choices[0].message.content or "").strip()
    obj = _extract_json(content)
    dom = obj.get("domains", {})
    if not isinstance(dom, dict):
        return _mock_plan(concept, domains)
    out: dict[str, list[str]] = {}
    for d in domains:
        xs = dom.get(d, [])
        if isinstance(xs, list) and xs:
            out[d] = [str(x) for x in xs[:6]]
        else:
            out[d] = _mock_plan(concept, [d]).get(d, [concept])
    return out

