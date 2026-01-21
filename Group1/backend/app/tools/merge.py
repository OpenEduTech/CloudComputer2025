from __future__ import annotations

import re

from dataclasses import dataclass
import re

from app.models import Edge, Node


@dataclass(frozen=True)
class MergeStats:
    nodes_merged: int = 0
    edges_removed: int = 0
    conflicts_flagged: int = 0


_ABBREV = {
    "nn": "neural network",
    "ml": "machine learning",
    "dl": "deep learning",
    "kl divergence": "kullback leibler divergence",
}


def _normalize_name(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"\(.*?\)", "", s)  # remove parenthetical
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return _ABBREV.get(s, s)


def _k(name: str, domain: str) -> str:
    s = _normalize_name(name)
    return f"{domain.lower()}::{s}"


def merge_synonyms(nodes: list[Node], edges: list[Edge]) -> tuple[list[Node], list[Edge], MergeStats]:
    """
    Very light de-dup:
    - merge nodes by (domain, normalized name)
    - rewrite edges to merged node ids
    """
    id_map: dict[str, str] = {}
    kept: dict[str, Node] = {}
    nodes_merged = 0

    for n in nodes:
        key = _k(n.name, n.domain)
        if key not in kept:
            kept[key] = n
        else:
            nodes_merged += 1
        id_map[n.id] = kept[key].id

    out_edges: dict[tuple[str, str, str], Edge] = {}
    edges_removed = 0
    for e in edges:
        s = id_map.get(e.source, e.source)
        t = id_map.get(e.target, e.target)
        k = (s, t, e.relation)
        e.source = s
        e.target = t
        e.ensure_id()

        if k not in out_edges:
            out_edges[k] = e
            continue

        # duplicate edge: keep higher confidence, but merge evidence by appending snippet (simple)
        cur = out_edges[k]
        if cur.confidence >= e.confidence:
            edges_removed += 1
            if e.evidence.snippet and e.evidence.snippet not in (cur.evidence.snippet or ""):
                cur.evidence.snippet = (cur.evidence.snippet or "").strip() + "\n" + e.evidence.snippet.strip()
            cur.flags = list({*(cur.flags or []), "duplicate"})
            out_edges[k] = cur
        else:
            edges_removed += 1
            if cur.evidence.snippet and cur.evidence.snippet not in (e.evidence.snippet or ""):
                e.evidence.snippet = (e.evidence.snippet or "").strip() + "\n" + cur.evidence.snippet.strip()
            e.flags = list({*(e.flags or []), "duplicate"})
            out_edges[k] = e

    # conflict marking: same (source,target) but multiple different relations
    by_pair: dict[tuple[str, str], set[str]] = {}
    for (s, t, rel) in out_edges.keys():
        by_pair.setdefault((s, t), set()).add(rel)

    conflicts_flagged = 0
    for (s, t), rels in by_pair.items():
        if len(rels) <= 1:
            continue
        for rel in rels:
            e = out_edges[(s, t, rel)]
            if "conflict" not in (e.flags or []):
                e.flags.append("conflict")
                conflicts_flagged += 1
            e.confidence = max(0.0, min(1.0, e.confidence * 0.8))
            out_edges[(s, t, rel)] = e

    stats = MergeStats(nodes_merged=nodes_merged, edges_removed=edges_removed, conflicts_flagged=conflicts_flagged)
    return list(kept.values()), list(out_edges.values()), stats

