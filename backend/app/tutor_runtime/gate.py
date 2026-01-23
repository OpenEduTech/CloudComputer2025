from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from app.tutor_runtime.base import CheckResult, CheckStatus, Checker


def run_with_checker(
    llm_call: Callable[[str], str],
    prompt: str,
    checker: Checker,
    context: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
) -> Tuple[str, Any]:
    """Call LLM and validate with checker.

    - PASS: returns (raw_output, parsed_output)
    - RETRY: retries up to max_retries
    - ESCALATE: raises RuntimeError with the checker reason
    """

    last_raw = ""
    ctx = context or {}

    for attempt in range(max_retries + 1):
        raw = llm_call(prompt)
        last_raw = raw

        result: CheckResult = checker.run(raw, ctx)
        if result.status == CheckStatus.PASS:
            return raw, result.output
        if result.status == CheckStatus.ESCALATE:
            raise RuntimeError(f"{checker.name} check failed: {result.reason}")

        # RETRY: append feedback to prompt to steer LLM
        prompt = (
            prompt
            + "\n\n"
            + f"[CHECKER_FEEDBACK] 上一轮输出未通过校验({checker.name})：{result.reason}。"
            + "请严格按要求修正后只输出 JSON。"
        )

    # exhausted retries
    raise RuntimeError(f"{checker.name} check failed after retries")
