from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

DISCIPLINE_ALIAS = {
    "数学": "数学",
    "物理学": "物理",
    "计算机科学": "计算机",
    "生物学": "生物",
    "哲学/社会科学": "社会学",
    # 兼容变体
    "社会科学": "社会学",
    "哲学": "社会学",
    "社会学": "社会学",
    "计算机": "计算机",
    "物理": "物理",
    "生物": "生物",
}

ALLOWED_CATEGORIES = ["数学", "物理学", "计算机科学", "生物学", "哲学/社会科学"]

def extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object found in model output")
    return json.loads(m.group(0))

def normalize_discipline(cat: str) -> Optional[str]:
    cat = (cat or "").strip()
    if not cat:
        return None
    if cat not in ALLOWED_CATEGORIES:
        # 允许一些别名
        if cat in DISCIPLINE_ALIAS:
            return DISCIPLINE_ALIAS[cat]
        return None
    return DISCIPLINE_ALIAS.get(cat, cat)

def shorten_text(s: str, max_len: int = 10) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"

def validate_and_fix(graph: Dict[str, Any], max_nodes: int, max_links: int) -> Dict[str, Any]:
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])

    if not isinstance(nodes, list) or not isinstance(links, list):
        raise ValueError("Invalid graph structure: nodes/links must be lists")

    nodes = nodes[:max_nodes]
    links = links[:max_links]

    seen: Set[str] = set()
    cleaned_nodes: List[Dict[str, Any]] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id", "")).strip()
        name = str(n.get("name", "")).strip()
        cat = str(n.get("category", "")).strip()
        desc = str(n.get("description", "") or "").strip()

        if not nid or not name:
            continue
        if nid in seen:
            continue

        discipline = normalize_discipline(cat)
        if discipline is None:
            continue

        seen.add(nid)
        cleaned_nodes.append(
            {
                "id": nid,
                "name": name,
                "category": cat,
                "discipline": discipline,
                "description": desc,  # 允许为空，后面可补默认
            }
        )

    node_ids = {n["id"] for n in cleaned_nodes}

    cleaned_links: List[Dict[str, Any]] = []
    for e in links:
        if not isinstance(e, dict):
            continue
        s = str(e.get("source", "")).strip()
        t = str(e.get("target", "")).strip()
        r = str(e.get("relation", "")).strip()
        desc = str(e.get("description", "") or "").strip()

        if not s or not t or not r:
            continue
        if s not in node_ids or t not in node_ids:
            continue

        cleaned_links.append(
            {
                "source": s,
                "target": t,
                "relation": r,
                "label": r,                 # 兼容前端读 label
                "name": r,                  # 兼容前端读 name
                "relation_short": shorten_text(r, 10),
                "edge_label": shorten_text(r, 10),
                "description": desc,        # 边解释
            }
        )

    return {"nodes": cleaned_nodes, "links": cleaned_links}

def prune_isolated_nodes(
    nodes: List[Dict[str, Any]],
    links: List[Dict[str, Any]],
    concept: str,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    删除“完全不在任何边里出现”的孤立节点，避免前端出现飘在外面的点。
    但尽量保留 name==concept 的核心概念节点。
    """
    used: Set[str] = set()
    for e in links:
        used.add(e.get("source"))
        used.add(e.get("target"))

    kept = []
    pruned = 0
    for n in nodes:
        nid = n.get("id")
        name = n.get("name", "")
        if nid in used or (isinstance(name, str) and name.strip() == concept):
            kept.append(n)
        else:
            pruned += 1

    return kept, pruned

def compute_node_values_scaled(nodes: List[Dict[str, Any]], links: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    前端 symbolSize 常直接用 value。
    原来 1/2 太小 -> 放大到更可见的范围（10~50），仍保持相对大小。
    """
    deg = {n["id"]: 0 for n in nodes}
    for e in links:
        s = e.get("source")
        t = e.get("target")
        if s in deg:
            deg[s] += 1
        if t in deg:
            deg[t] += 1

    # 放大：value = 10 + deg*6，限制到 [10, 50]
    for k in list(deg.keys()):
        v = 10 + max(1, deg[k]) * 6
        deg[k] = max(10, min(50, v))
    return deg