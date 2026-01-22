from __future__ import annotations

from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.db.mongo import get_db


def _knowledge_nodes_col(db):
    return db["knowledge_nodes"]


def _mastery_col(db):
    return db["mastery"]


def _apply_student_filter(query: Dict[str, Any], student_id: Optional[str]) -> None:
    if not student_id:
        return
    if student_id == "demo_user":
        query["$or"] = [{"student_id": student_id}, {"student_id": {"$exists": False}}]
    else:
        query["student_id"] = student_id


def list_nodes(
    material_id: str,
    notebook_id: Optional[str] = None,
    student_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    db = get_db()
    query: Dict[str, Any] = {"material_id": material_id}
    if notebook_id:
        query["notebook_id"] = notebook_id
    _apply_student_filter(query, student_id)
    nodes = list(_knowledge_nodes_col(db).find(query).sort([("level", 1), ("order", 1)]))
    for n in nodes:
        n["id"] = str(n["_id"])
        n.pop("_id", None)
    return nodes


def get_mastery_stats_map(
    student_id: str,
    notebook_id: Optional[str],
    node_ids: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Return mastery stats keyed by node_id.

    We keep seen/correct so we can aggregate parent mastery as:
    sum(correct) / sum(seen)
    """
    if not student_id or not node_ids:
        return {}
    db = get_db()
    query: Dict[str, Any] = {"student_id": student_id, "node_id": {"$in": node_ids}}
    if notebook_id:
        query["notebook_id"] = notebook_id
    rows = list(_mastery_col(db).find(query, {"node_id": 1, "seen": 1, "correct": 1, "wrong": 1, "mastery_score": 1}))
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        nid = r.get("node_id")
        if not nid:
            continue
        out[str(nid)] = {
            "seen": int(r.get("seen", 0) or 0),
            "correct": int(r.get("correct", 0) or 0),
            "wrong": int(r.get("wrong", 0) or 0),
            "mastery_score": float(r.get("mastery_score", 0.0) or 0.0),
        }
    return out


def build_tree(
    material_id: str,
    student_id: Optional[str] = None,
    notebook_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    nodes = list_nodes(material_id, notebook_id=notebook_id, student_id=student_id)
    id_list = [n["id"] for n in nodes]
    mastery_stats = get_mastery_stats_map(student_id or "", notebook_id, id_list) if student_id else {}

    by_id: Dict[str, Dict[str, Any]] = {}
    children_map: Dict[Optional[str], List[Dict[str, Any]]] = {}

    for n in nodes:
        stats = mastery_stats.get(n["id"], {})
        n["self_seen"] = int(stats.get("seen", 0) or 0)
        n["self_correct"] = int(stats.get("correct", 0) or 0)
        n["self_wrong"] = int(stats.get("wrong", 0) or 0)
        n["self_mastery_score"] = float(stats.get("mastery_score", 0.0) or 0.0)
        # For leaves, mastery_score is self mastery. For parents, we will aggregate from children.
        n["mastery_score"] = n["self_mastery_score"]
        n["seen"] = n["self_seen"]
        n["correct"] = n["self_correct"]
        n["wrong"] = n["self_wrong"]
        n["children"] = []
        by_id[n["id"]] = n
        children_map.setdefault(n.get("parent_id"), []).append(n)

    # 挂孩子
    for parent_id, kids in children_map.items():
        if parent_id and parent_id in by_id:
            by_id[parent_id]["children"] = kids

    # 根节点：parent_id 为空 或 parent 不存在
    roots: List[Dict[str, Any]] = []
    for n in nodes:
        pid = n.get("parent_id")
        if not pid or pid not in by_id:
            roots.append(n)

    # M2 aggregation rule:
    # - Leaf nodes keep their own mastery (seen/correct).
    # - Parent nodes' mastery is computed from all descendant answers:
    #   mastery_score = sum(correct_children) / sum(seen_children)
    def _aggregate(node: Dict[str, Any]) -> Dict[str, int]:
        kids = node.get("children") or []
        if not kids:
            return {"seen": int(node.get("seen", 0) or 0), "correct": int(node.get("correct", 0) or 0), "wrong": int(node.get("wrong", 0) or 0)}

        seen_sum = 0
        correct_sum = 0
        wrong_sum = 0
        for k in kids:
            child_totals = _aggregate(k)
            seen_sum += int(child_totals.get("seen", 0) or 0)
            correct_sum += int(child_totals.get("correct", 0) or 0)
            wrong_sum += int(child_totals.get("wrong", 0) or 0)

        node["seen"] = seen_sum
        node["correct"] = correct_sum
        node["wrong"] = wrong_sum
        node["mastery_score"] = (correct_sum / seen_sum) if seen_sum > 0 else 0.0
        return {"seen": seen_sum, "correct": correct_sum, "wrong": wrong_sum}

    for r in roots:
        _aggregate(r)

    return roots
