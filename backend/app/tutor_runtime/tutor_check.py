from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.tutor_runtime.base import CheckResult, CheckStatus
from app.tutor_runtime.utils import safe_json_loads


_LEAK_PATTERNS = [
    re.compile(r"正确答案"),
    re.compile(r"答案是"),
    re.compile(r"选项\s*[A-D]"),
    re.compile(r"^\s*[A-D]\s*$", re.IGNORECASE),
    re.compile(r"final answer", re.IGNORECASE),
]

def _normalize_answer(ans: str) -> str:
    if ans is None:
        return ""
    s = str(ans).strip()
    # normalize common MCQ formats: 'A', '选A', '选项A', '答案：A'
    m = re.search(r"([A-D])", s, re.IGNORECASE)
    if m and len(s) <= 8:
        return m.group(1).upper()
    # whitespace normalization for free-form answers
    s = re.sub(r"\s+", " ", s)
    return s



class TutorCheck:
    """Validate tutor output for controlled hint ladder."""

    name = "tutor"

    def run(self, raw_output: Any, context: Optional[Dict[str, Any]] = None) -> CheckResult:
        ok, data, err = safe_json_loads(str(raw_output))
        if not ok:
            return CheckResult(status=CheckStatus.RETRY, reason=err)
        if not isinstance(data, dict):
            return CheckResult(status=CheckStatus.RETRY, reason="tutor output must be an object")

        ctx = context or {}
        hint_level = str(ctx.get("hint_level") or data.get("hint_level") or "").upper()
        is_final = hint_level in {"FINAL", "END"}

        combined_text = " ".join([str(v) for v in data.values()])
        if len(combined_text) > 900:
            return CheckResult(status=CheckStatus.RETRY, reason="tutor hint too long; provide one-step guidance")
        if len(re.findall(r"\b\d+\.", combined_text)) >= 2:
            return CheckResult(status=CheckStatus.RETRY, reason="tutor should give only one step per turn")

        if not is_final:
            for pat in _LEAK_PATTERNS:
                if pat.search(combined_text):
                    return CheckResult(status=CheckStatus.RETRY, reason="hint_level < FINAL: do not reveal final answer", output=data)

        # FINAL stage: if we have a reference correct_answer, ensure tutor's final answer is consistent
        if is_final and context and context.get("correct_answer"):
            ref = _normalize_answer(str(context.get("correct_answer")))
            cand = _normalize_answer(str(data.get("final_answer") or data.get("worked_solution") or ""))
            if ref and cand and ref != cand:
                return CheckResult(
                    status=CheckStatus.RETRY,
                    reason=f"FINAL answer mismatch: expected {ref} but got {cand}",
                    output=data,
                )
        if not data.get("hint") and not data.get("question"):
            return CheckResult(status=CheckStatus.RETRY, reason="tutor output must include hint or question")

        return CheckResult(status=CheckStatus.PASS, output=data)
