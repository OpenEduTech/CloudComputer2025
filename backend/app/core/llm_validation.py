"""
LLM响应校验工具
"""
from __future__ import annotations
from typing import Any, Dict, List


def _base_report(kind: str, raw: str | None) -> Dict[str, Any]:
    preview = (raw or "").strip().replace("\n", " ")
    return {
        "kind": kind,
        "valid": True,
        "issues": [],
        "warnings": [],
        "raw_preview": preview[:300]
    }


def validate_questions_response(raw: str, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    report = _base_report("question_generation", raw)
    if not questions:
        report["valid"] = False
        report["issues"].append("未解析出任何题目")
        return report

    for idx, q in enumerate(questions, start=1):
        content = (q.get("content") or "").strip()
        if len(content) < 8:
            report["warnings"].append(f"第{idx}题内容过短")
        if not q.get("correct_answer"):
            report["issues"].append(f"第{idx}题缺少正确答案")
        q_type = (q.get("question_type") or q.get("type") or "").lower()
        if q_type == "choice":
            options = q.get("options") or []
            if len(options) < 2:
                report["issues"].append(f"第{idx}题选项不足")
    if report["issues"]:
        report["valid"] = False
    return report


def validate_evaluation_response(raw: str, evaluation: Dict[str, Any]) -> Dict[str, Any]:
    report = _base_report("answer_evaluation", raw)
    score = evaluation.get("score")
    if score is None:
        report["issues"].append("评分缺失")
    else:
        try:
            score_val = float(score)
            if score_val < 0 or score_val > 100:
                report["warnings"].append("评分超出0-100范围")
        except Exception:
            report["warnings"].append("评分不是数字")
    if not evaluation.get("detailed_feedback"):
        report["warnings"].append("反馈为空")
    if report["issues"]:
        report["valid"] = False
    return report


def validate_knowledge_response(raw: str, expansion: Dict[str, Any]) -> Dict[str, Any]:
    report = _base_report("knowledge_expansion", raw)
    if not (expansion.get("explanation") or "").strip():
        report["issues"].append("扩充解释为空")
    if report["issues"]:
        report["valid"] = False
    return report


def validate_outline_summary(raw: str, summary: List[str] | None) -> Dict[str, Any]:
    report = _base_report("outline_summary", raw)
    if not summary:
        report["issues"].append("目录概括为空")
    if report["issues"]:
        report["valid"] = False
    return report
