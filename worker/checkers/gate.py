from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from .base import BaseChecker, CheckResult, CheckStatus


def run_with_checker(
    prompt: str,
    call_llm: Callable[[str], str],
    checker: BaseChecker,
    context: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
) -> Tuple[Any, CheckResult]:
    """Call LLM and apply checker with PASS/RETRY/ESCALATE.

    Returns (output, final_check_result). When PASS, `output` is the normalized
    checker output. When ESCALATE, `output` may be None.

    Retry strategy:
    - On RETRY, append a short repair instruction to the original prompt
      using the checker reason.
    """

    ctx = context or {}
    last: Optional[CheckResult] = None

    for attempt in range(max_retries + 1):
        used_prompt = prompt
        if attempt > 0 and last is not None:
            used_prompt = (
                prompt
                + "\n\n"
                + "IMPORTANT: Your previous output had issues. "
                + "Fix them and output JSON only. Issues: "
                + (last.reason or "validation failed")
                + "\n"
            )

        raw = call_llm(used_prompt)
        result = checker.run(raw, ctx)
        last = result

        if result.status == CheckStatus.PASS:
            return result.output, result
        if result.status == CheckStatus.ESCALATE:
            return result.output, result
        # RETRY -> continue loop

    # exhausted retries
    if last is None:
        last = CheckResult(status=CheckStatus.ESCALATE, reason="no output")
    return last.output, last
