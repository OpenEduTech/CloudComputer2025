from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import Edge, Evidence, Node
from app.tools.seed_corpus import Passage


@dataclass(frozen=True)
class Extracted:
    nodes: list[Node]
    edges: list[Edge]


def _slug(s: str) -> str:
    raw = s.strip().lower()
    # keep ascii word chars + CJK, replace others with underscore
    raw = re.sub(r"[^\w\u4e00-\u9fff]+", "_", raw, flags=re.UNICODE)
    raw = re.sub(r"_+", "_", raw).strip("_")
    if raw:
        return raw
    # fallback to stable hash so different concepts don't collapse to the same id
    import hashlib

    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()[:10]


def _make_node(*, name: str, domain: str, definition: str | None, confidence: float) -> Node:
    return Node(
        id=f"{_slug(domain)}:{_slug(name)}",
        name=name,
        domain=domain,
        definition=definition,
        confidence=confidence,
    )


def graph_from_passages(concept: str, passages: list[Passage]) -> Extracted:
    """
    Offline extraction:
    - build 1 node per passage title
    - connect concept -> passage concept nodes
    - add a couple of canonical relations when keywords appear
    """
    concept_node = _make_node(name=concept, domain="Core", definition=f"User query concept: {concept}", confidence=0.9)
    nodes: dict[str, Node] = {concept_node.id: concept_node}
    edges: list[Edge] = []

    for p in passages:
        n = _make_node(name=p.title.replace("(seed)", "").strip(), domain=p.domain, definition=p.snippet, confidence=0.78)
        nodes.setdefault(n.id, n)

        # heuristic relation
        rel = "related_to"
        sn = p.snippet.lower()
        if "loss function" in sn or "classification" in sn:
            rel = "used_in"
        elif "second law" in sn or "thermodynamics" in sn:
            rel = "explains"
        elif "probability distribution" in sn or "distributions" in sn:
            rel = "is_a"

        edges.append(
            Edge(
                source=concept_node.id,
                target=n.id,
                relation=rel,  # type: ignore[arg-type]
                explanation=f"{concept} is connected to {n.name} in the domain of {p.domain}.",
                evidence=Evidence(title=p.title, snippet=p.snippet, url=p.url, domain=p.domain),
                confidence=0.72,
                checked=True,
            )
        )

    return Extracted(nodes=list(nodes.values()), edges=edges)


def bridge_discovery(extracted: Extracted) -> Extracted:
    """
    Add a simple 'bridge' concept across domains by connecting top nodes to a synthetic bridge.
    This makes the demo visibly cross-disciplinary even in offline mode.
    """
    nodes = {n.id: n for n in extracted.nodes}
    edges = list(extracted.edges)

    domains = sorted({n.domain for n in nodes.values() if n.domain not in ("Core",)})
    if len(domains) < 2:
        return extracted

    bridge = _make_node(
        name="Uncertainty",
        domain="Bridge",
        definition="A bridge concept used to connect multiple disciplines via uncertainty/information viewpoints.",
        confidence=0.74,
    )
    nodes.setdefault(bridge.id, bridge)

    for d in domains[:4]:
        # connect one representative node in that domain to bridge
        candidate = next((n for n in nodes.values() if n.domain == d), None)
        if not candidate:
            continue
        edges.append(
            Edge(
                source=candidate.id,
                target=bridge.id,
                relation="bridges",
                explanation=f"{candidate.name} can be interpreted through uncertainty; this bridges {d} with other domains.",
                evidence=Evidence(title="Bridge rationale", snippet=candidate.definition or "", url=None),
                confidence=0.62,
                checked=True,
            )
        )

    return Extracted(nodes=list(nodes.values()), edges=edges)

