from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class CheckStatus(str, Enum):
    """Tri-state result for the check layer."""

    PASS = "PASS"
    RETRY = "RETRY"
    ESCALATE = "ESCALATE"


@dataclass
class CheckResult:
    """Result returned by a checker.

    - status: PASS/RETRY/ESCALATE
    - reason: human-readable reason (also used for repair prompts)
    - output: normalized/parsed object for PASS; optional for RETRY/ESCALATE
    - fixed_output: optional fixed raw string (rare; most checkers normalize to `output`)
    - meta: any extra info (e.g., violations) useful for logging
    """

    status: CheckStatus
    reason: str = ""
    output: Optional[Any] = None
    fixed_output: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class BaseChecker:
    """Base class for all checkers."""

    name: str = "base"

    def run(self, raw_output: Any, context: Optional[Dict[str, Any]] = None) -> CheckResult:
        raise NotImplementedError
