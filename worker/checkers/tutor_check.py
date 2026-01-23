from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .base import BaseChecker, CheckResult, CheckStatus
from .utils import safe_json_loads


_LEAK_PATTERNS = [
    re.compile(r"正确答案"),
    re.compile(r"答案是"),
    re.compile(r"选项\s*[A-D]"),
    re.compile(r"^\s*[A-D]\s*$", re.IGNORECASE),
    re.compile(r"final answer", re.IGNORECASE),
]


class TutorCheck(BaseChecker):
    """Validate tutor hint output.

    Requirements (minimal):
    - For hint_level < FINAL, should NOT reveal final answer.
    - Encourage one-step guidance (keep output concise).

    We keep the schema flexible. Recommended JSON fields:
      {"hint": "...", "question": "...", "hint_level": "L1"}
    """

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

        # Conciseness guard: avoid multi-step solution dumps
        # (heuristic: too long, or contains multiple numbered steps)
        combined_text = " ".join([str(v) for v in data.values()])
        if len(combined_text) > 800:
            return CheckResult(status=CheckStatus.RETRY, reason="tutor hint too long; provide one-step guidance")
        if len(re.findall(r"\b\d+\.", combined_text)) >= 2:
            return CheckResult(status=CheckStatus.RETRY, reason="tutor should give only one step per turn")

        if not is_final:
            for pat in _LEAK_PATTERNS:
                if pat.search(combined_text):
                    return CheckResult(
                        status=CheckStatus.RETRY,
                        reason="hint_level < FINAL: do not reveal final answer",
                        output=data,
                    )

        # ensure at least one of hint or question exists
        if not data.get("hint") and not data.get("question"):
            return CheckResult(status=CheckStatus.RETRY, reason="tutor output must include hint or question")

        return CheckResult(status=CheckStatus.PASS, output=data)
