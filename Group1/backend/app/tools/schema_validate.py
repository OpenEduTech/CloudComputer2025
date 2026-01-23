from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.models import GraphResult
from app.config import settings


def validate_graph(graph_dict: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Schema validation backed by Pydantic models.
    Returns (ok, errors).
    """
    try:
        GraphResult.model_validate(graph_dict)
        return True, []
    except ValidationError as e:
        errs: list[str] = []
        for err in e.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "invalid")
            errs.append(f"{loc}: {msg}".strip(": "))
        return False, errs


def light_fix(graph_dict: dict[str, Any], errors: list[str]) -> tuple[dict[str, Any], int]:
    """
    Best-effort fix to make the dict pass schema:
    - fill missing keys
    - ensure evidence.title/snippet exist
    - add flags/check_reason defaults
    - add edge.id if missing (hash)
    - infer evidence.domain from target node domain when possible
    Returns (fixed_graph_dict, fixed_count).
    """
    fixed = 0
    g = dict(graph_dict)
    g.setdefault("concept", "Unknown"); fixed += 1 if "concept" not in graph_dict else 0
    g.setdefault("nodes", []); fixed += 1 if "nodes" not in graph_dict else 0
    g.setdefault("edges", []); fixed += 1 if "edges" not in graph_dict else 0
    g.setdefault("meta", {}); fixed += 1 if "meta" not in graph_dict else 0

    meta = dict(g.get("meta") or {})
    meta.setdefault("generated_at", ""); fixed += 1 if "generated_at" not in meta else 0
    meta.setdefault("version", "v1"); fixed += 1 if "version" not in meta else 0
    meta.setdefault("checker_summary", {}); fixed += 1 if "checker_summary" not in meta else 0
    g["meta"] = meta

    # index nodes by id for inference
    node_domain: dict[str, str] = {}
    for n in list(g.get("nodes") or []):
        if isinstance(n, dict) and n.get("id") and n.get("domain"):
            node_domain[str(n["id"])] = str(n["domain"])

    def _sha(source: str, relation: str, target: str) -> str:
        import hashlib

        s = f"{source}|{relation}|{target}".encode("utf-8", "ignore")
        return hashlib.sha1(s).hexdigest()[:12]

    fixed_edges: list[dict[str, Any]] = []
    for e in list(g.get("edges") or []):
        if not isinstance(e, dict):
            continue
        ee = dict(e)
        if "flags" not in ee or not isinstance(ee.get("flags"), list):
            ee["flags"] = []
            fixed += 1
        ee.setdefault("check_reason", None)

        ev = ee.get("evidence") if isinstance(ee.get("evidence"), dict) else {}
        if not isinstance(ev, dict):
            ev = {}
        if "title" not in ev:
            ev["title"] = ""
            fixed += 1
        if "snippet" not in ev:
            ev["snippet"] = ""
            fixed += 1
        if "url" not in ev:
            ev["url"] = None
        if "domain" not in ev:
            # infer from target node
            tid = str(ee.get("target") or "")
            ev["domain"] = node_domain.get(tid)
            fixed += 1
        ee["evidence"] = ev

        if not ee.get("id") and ee.get("source") and ee.get("target") and ee.get("relation"):
            ee["id"] = _sha(str(ee["source"]), str(ee["relation"]), str(ee["target"]))
            fixed += 1

        fixed_edges.append(ee)
    g["edges"] = fixed_edges

    return g, fixed


async def llm_fix(graph_dict: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    """
    Optional (future): use OpenAI-compatible LLM to repair the JSON.
    For now, return as-is so the system stays offline-runnable.
    """
    if settings.llm_provider != "openai_compat":
        return graph_dict
    if not settings.openai_api_key:
        return graph_dict

    try:
        from app.tools.llm_openai_compat import json_fix

        return json_fix(graph_dict, errors)
    except Exception:
        # Never break the pipeline because of LLM issues
        return graph_dict

