"""LLM Check Layer (通用闸门).

This package provides reusable guardrails for LLM outputs.
Each checker returns a tri-state decision:

- PASS: output is acceptable (possibly after normalization)
- RETRY: output is unacceptable, but can likely be repaired by retrying the LLM
- ESCALATE: output is unsafe / irrecoverable; caller should stop or downgrade

The intent is to make Coach/Tutor safer and more deterministic, while
also improving M1/M2 stability (quiz generation & grading).
"""

from .base import CheckResult, CheckStatus, BaseChecker

__all__ = ["CheckResult", "CheckStatus", "BaseChecker"]
