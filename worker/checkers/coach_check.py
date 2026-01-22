from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .base import BaseChecker, CheckResult, CheckStatus
from .utils import safe_json_loads


class CoachCheck(BaseChecker):
    """Validate coach output.

    The key requirement for M3 is: the suggestion must be grounded on
    the student's actual issues, i.e., it should reference at least one of:
    - missing_points
    - error_tags
    - weak_node_ids

    We keep this checker permissive (no strict schema), but enforce grounding.
    """

    name = "coach"

    def run(self, raw_output: Any, context: Optional[Dict[str, Any]] = None) -> CheckResult:
        ok, data, err = safe_json_loads(str(raw_output))
        if not ok:
            return CheckResult(status=CheckStatus.RETRY, reason=err)
        if not isinstance(data, dict):
            return CheckResult(status=CheckStatus.RETRY, reason="coach output must be an object")

        ctx = context or {}
        missing_points = ctx.get("missing_points") or []
        error_tags = ctx.get("error_tags") or []
        weak_node_ids = ctx.get("weak_node_ids") or []

        # If context doesn't contain these, don't block.
        if not missing_points and not error_tags and not weak_node_ids:
            return CheckResult(status=CheckStatus.PASS, output=data)

        haystack = json.dumps(data, ensure_ascii=False)

        def _has_any(items):
            for it in items:
                s = str(it)
                if s and s in haystack:
                    return True
            return False

        if _has_any(missing_points) or _has_any(error_tags) or _has_any(weak_node_ids):
            return CheckResult(status=CheckStatus.PASS, output=data)

        return CheckResult(
            status=CheckStatus.RETRY,
            reason="coach must reference missing_points or error_tags or weak_node_ids from context",
            output=data,
        )
