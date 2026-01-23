from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseChecker, CheckResult, CheckStatus
from .utils import safe_json_loads


class QuizCheck(BaseChecker):
    """Validate quiz generation output.

    Expected normalized output: List[Dict] questions.
    """

    name = "quiz"

    def __init__(self, expected_count: Optional[int] = None):
        self.expected_count = expected_count

    def run(self, raw_output: Any, context: Optional[Dict[str, Any]] = None) -> CheckResult:
        ok, data, err = safe_json_loads(str(raw_output))
        if not ok:
            return CheckResult(status=CheckStatus.RETRY, reason=err)

        if isinstance(data, dict) and "questions" in data:
            data = data.get("questions")

        if not isinstance(data, list):
            return CheckResult(status=CheckStatus.RETRY, reason="questions should be a list")

        questions: List[Dict[str, Any]] = []
        for i, q in enumerate(data):
            if not isinstance(q, dict):
                return CheckResult(status=CheckStatus.RETRY, reason=f"question[{i}] must be an object")

            qtype = q.get("type")
            if qtype not in {"mcq", "blank", "short"}:
                return CheckResult(status=CheckStatus.RETRY, reason=f"question[{i}] invalid type")

            stem = q.get("stem")
            if not isinstance(stem, str) or not stem.strip():
                return CheckResult(status=CheckStatus.RETRY, reason=f"question[{i}] missing stem")

            answer_key = q.get("answer_key")
            if answer_key is None or (isinstance(answer_key, str) and not answer_key.strip()):
                return CheckResult(status=CheckStatus.RETRY, reason=f"question[{i}] missing answer_key")

            difficulty = q.get("difficulty")
            if difficulty not in {"L1", "L2", "L3"}:
                return CheckResult(status=CheckStatus.RETRY, reason=f"question[{i}] invalid difficulty")

            if qtype == "mcq":
                options = q.get("options") or []
                if not isinstance(options, list) or len(options) < 3:
                    return CheckResult(status=CheckStatus.RETRY, reason=f"question[{i}] mcq options invalid")

            if qtype == "short":
                rubric = q.get("rubric")
                if not isinstance(rubric, str) or not rubric.strip():
                    return CheckResult(status=CheckStatus.RETRY, reason=f"question[{i}] short missing rubric")

            node_titles = q.get("node_titles")
            if node_titles is not None and not isinstance(node_titles, list):
                return CheckResult(status=CheckStatus.RETRY, reason=f"question[{i}] node_titles must be an array")

            # normalize strings
            q["stem"] = stem.strip()
            if isinstance(answer_key, str):
                q["answer_key"] = answer_key.strip()
            questions.append(q)

        # count mismatch: do not hard-fail (demo friendly). Only warn in meta.
        meta = {}
        if self.expected_count is not None and len(questions) != self.expected_count:
            meta["count_mismatch"] = {"expected": self.expected_count, "got": len(questions)}

        return CheckResult(status=CheckStatus.PASS, output=questions, meta=meta or None)
