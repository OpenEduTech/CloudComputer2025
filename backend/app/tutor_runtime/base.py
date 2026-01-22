from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Protocol, Tuple


class CheckStatus(str, Enum):
    PASS = "PASS"
    RETRY = "RETRY"
    ESCALATE = "ESCALATE"


@dataclass
class CheckResult:
    status: CheckStatus
    reason: str = ""
    output: Optional[Any] = None


class Checker(Protocol):
    name: str

    def run(self, raw_output: Any, context: Optional[Dict[str, Any]] = None) -> CheckResult: ...
