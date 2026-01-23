from __future__ import annotations

from typing import Any, Dict, Optional

from .base import BaseChecker, CheckResult, CheckStatus
from .utils import safe_json_loads


class GradeCheck(BaseChecker):
    """Validate grading output for short/blank answers.

    Expected fields (at minimum):
    - score: float 0..1
    - is_correct: bool
    - missing_points: list[str]
    - error_tags: list[str]
    - error_analysis: str
    - feedback: str

    Normalizes types and clamps score.
    """

    name = "grade"

    def run(self, raw_output: Any, context: Optional[Dict[str, Any]] = None) -> CheckResult:
        ok, data, err = safe_json_loads(str(raw_output))
        if not ok:
            return CheckResult(status=CheckStatus.RETRY, reason=err)
        if not isinstance(data, dict):
            return CheckResult(status=CheckStatus.RETRY, reason="grading result must be an object")

        if "score" not in data:
            return CheckResult(status=CheckStatus.RETRY, reason="grading result missing score")

        try:
            score = float(data.get("score", 0.0) or 0.0)
        except Exception:
            return CheckResult(status=CheckStatus.RETRY, reason="score must be a number")
        if score < 0.0:
            score = 0.0
        if score > 1.0:
            score = 1.0
        data["score"] = score

        is_correct = data.get("is_correct")
        if isinstance(is_correct, bool):
            pass
        elif isinstance(is_correct, (int, float)):
            data["is_correct"] = bool(is_correct)
        elif isinstance(is_correct, str):
            data["is_correct"] = is_correct.strip().lower() in {"true", "yes", "1"}
        else:
            # derive from score as fallback
            data["is_correct"] = score >= 0.99

        # normalize list fields
        mp = data.get("missing_points")
        if mp is None:
            mp = []
        if not isinstance(mp, list):
            return CheckResult(status=CheckStatus.RETRY, reason="missing_points must be an array")
        data["missing_points"] = [str(x) for x in mp]

        tags = data.get("error_tags")
        if tags is None:
            tags = []
        if not isinstance(tags, list):
            return CheckResult(status=CheckStatus.RETRY, reason="error_tags must be an array")
        data["error_tags"] = [str(x) for x in tags]

        ea = data.get("error_analysis")
        if ea is None:
            ea = ""
        if not isinstance(ea, str):
            ea = str(ea)
        data["error_analysis"] = ea

        fb = data.get("feedback")
        if fb is None:
            fb = ""
        if not isinstance(fb, str):
            fb = str(fb)
        data["feedback"] = fb

        return CheckResult(status=CheckStatus.PASS, output=data)
