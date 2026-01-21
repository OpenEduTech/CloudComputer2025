from __future__ import annotations

import re

from app.models import Edge, GraphResult


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def evidence_check(edge: Edge, *, source_name: str, target_name: str) -> tuple[bool, float, str]:
    """
    Very lightweight "check layer" for offline demo:
    - evidence snippet must be non-empty
    - explanation and snippet should share at least one keyword token
    """
    # Hard rules (Layer 0)
    if not (edge.evidence and edge.evidence.title and edge.evidence.snippet):
        return False, 0.0, "Missing evidence.title or evidence.snippet."
    if not (edge.explanation or "").strip():
        return False, 0.0, "Missing explanation."

    sn = _norm(edge.evidence.snippet)
    sname = _norm(source_name)
    tname = _norm(target_name)
    if not sn:
        return False, 0.0, "Empty evidence snippet."

    # require snippet mention at least one endpoint (name or key token)
    def _mentions(name: str) -> bool:
        if not name:
            return False
        parts = [p for p in name.split(" ") if len(p) >= 4]
        if not parts:
            return name in sn
        return any(p in sn for p in parts[:4])

    if not (_mentions(sname) or _mentions(tname)):
        return False, 0.15, "Evidence snippet does not mention source/target concept."

    # Layer 1 (stronger rule): explanation should share keywords with snippet
    exp = _norm(edge.explanation)
    tokens = {t for t in sn.split(" ") if len(t) >= 6}
    overlap = sum(1 for t in list(tokens)[:12] if t in exp)
    score = _clamp01(0.55 + 0.07 * overlap)
    return True, score, "Evidence supports the relation."


def run_check(graph: GraphResult, strict: bool = True) -> GraphResult:
    passed = 0
    failed = 0
    downgraded = 0
    checked_total = 0
    node_name = {n.id: n.name for n in graph.nodes}
    edges: list[Edge] = []

    for e in graph.edges:
        e.ensure_id()
        checked_total += 1
        sname = node_name.get(e.source, e.source)
        tname = node_name.get(e.target, e.target)

        # relation whitelist + optional downgrade
        if e.relation not in ("related_to", "used_in", "is_a", "explains", "bridges"):
            e.relation = "related_to"  # type: ignore[assignment]
            e.flags.append("downgraded")
            downgraded += 1

        ok, score, reason = evidence_check(e, source_name=sname, target_name=tname)
        if ok:
            passed += 1
            e.checked = True
            e.confidence = _clamp01((e.confidence + score) / 2)
            e.check_reason = reason
        else:
            failed += 1
            e.checked = False
            e.confidence = _clamp01(e.confidence * 0.45)
            e.check_reason = reason
            if strict:
                e.explanation = e.explanation or "No supported evidence found; marked as unchecked."
        edges.append(e)

    graph.edges = edges
    graph.meta.checker_summary.passed = passed
    graph.meta.checker_summary.failed = failed
    graph.meta.checker_summary.edges_checked = checked_total
    graph.meta.checker_summary.edges_failed = failed
    graph.meta.checker_summary.edges_downgraded = downgraded
    return graph

