from __future__ import annotations
import re
from typing import Any, Dict, List, Set, Tuple

GENERIC_REL_PATTERNS = [
    r"有关", r"相关", r"联系", r"关系", r"影响", r"作用", r"涉及", r"包含", r"属于",
    r"是一种", r"一种", r"类似", r"相似", r"相互", r"关联"
]

INFORMATIVE_REL_KEYWORDS = [
    "用于", "导致", "推导", "定义", "推广", "对应", "解释", "建模", "优化", "学习",
    "编码", "度量", "估计", "约束", "预测", "控制", "演化", "证明", "依赖", "实现"
]

def is_generic_relation(rel: str) -> bool:
    rel = (rel or "").strip()
    if not rel:
        return True
    for pat in GENERIC_REL_PATTERNS:
        if re.search(pat, rel):
            return True
    return False

def is_informative_relation(rel: str, min_len: int, max_len: int) -> bool:
    """
    减少误杀，避免边太少导致断开。
    """
    rel = (rel or "").strip()
    if len(rel) < min_len or len(rel) > max_len:
        return False

    # 如果完全是空泛词，并且不包含任何信息量关键词，则判为不合格
    if is_generic_relation(rel) and all(k not in rel for k in INFORMATIVE_REL_KEYWORDS):
        return False

    # 有信息量关键词 -> 放行
    if any(k in rel for k in INFORMATIVE_REL_KEYWORDS):
        return True

    # 否则只要不是特别空泛，也放行一部分
    # （比如“宏观微观视角相对应/基础/前提/扩展”等）
    if re.search(r"基础|前提|推广|对应|解释|定义|推导|建模|优化|估计|预测|扩展|衍生|来源|应用|约束", rel):
        return True

    # 最后兜底：不是空泛就放行
    return not is_generic_relation(rel)

def content_check(
    nodes: List[Dict[str, Any]],
    links: List[Dict[str, Any]],
    *,
    min_disciplines: int,
    min_valid_links: int,
    min_relation_len: int,
    max_relation_len: int,
    max_generic_rel_ratio: float,
    min_cross_discipline_edge_ratio: float,
) -> Dict[str, Any]:
    warnings: List[str] = []

    # 1) 过滤 relation（但保留被过滤列表，后面可“放宽”）
    kept_links: List[Dict[str, Any]] = []
    filtered_links: List[Dict[str, Any]] = []

    total_rel = 0
    generic_total = 0
    generic_filtered = 0

    for e in links:
        rel = str(e.get("relation", "")).strip()
        if not rel:
            continue

        total_rel += 1
        if is_generic_relation(rel):
            generic_total += 1

        if not is_informative_relation(rel, min_relation_len, max_relation_len):
            if is_generic_relation(rel):
                generic_filtered += 1
            filtered_links.append(e)
            continue

        kept_links.append(e)

    if len(kept_links) < len(links):
        warnings.append(f"content_check: filtered {len(links) - len(kept_links)} low-quality relations")

    # 把 generic_filtered 写进 warnings
    if generic_filtered > 0:
        warnings.append(f"content_check: generic relations filtered = {generic_filtered}")

    # 2) 学科覆盖
    disciplines: Set[str] = set()
    for n in nodes:
        d = n.get("discipline")
        if isinstance(d, str) and d.strip():
            disciplines.add(d.strip())

    if len(disciplines) < min_disciplines:
        warnings.append(
            f"content_check: discipline coverage too low ({len(disciplines)}<{min_disciplines}), disciplines={sorted(disciplines)}"
        )

    # 3) 跨学科边比例（基于 kept_links）
    id2disc = {n.get("id"): n.get("discipline") for n in nodes if isinstance(n.get("id"), str)}
    cross_cnt = 0
    edge_cnt = 0
    for e in kept_links:
        s = e.get("source")
        t = e.get("target")
        if s not in id2disc or t not in id2disc:
            continue
        ds = id2disc.get(s)
        dt = id2disc.get(t)
        if not isinstance(ds, str) or not isinstance(dt, str):
            continue
        edge_cnt += 1
        if ds != dt:
            cross_cnt += 1

    cross_ratio = (cross_cnt / edge_cnt) if edge_cnt > 0 else 0.0
    if edge_cnt > 0 and cross_ratio < min_cross_discipline_edge_ratio:
        warnings.append(
            f"content_check: cross-discipline edge ratio too low ({cross_ratio:.2f} < {min_cross_discipline_edge_ratio}), cross={cross_cnt}/{edge_cnt}"
        )

    # 4) 空泛关系占比（不再第二次遍历 links，直接用上面统计）
    generic_ratio = (generic_total / total_rel) if total_rel > 0 else 1.0
    if total_rel > 0 and generic_ratio > max_generic_rel_ratio:
        warnings.append(
            f"content_check: too many generic relations (ratio={generic_ratio:.2f} > {max_generic_rel_ratio})"
        )

    # 5) 边太少：先 warning
    if len(kept_links) < min_valid_links:
        warnings.append(
            f"content_check: too few valid links after filtering ({len(kept_links)}<{min_valid_links})"
        )

        # 为了避免“节点断开”，这里自动放宽过滤，补回一些边到 min_valid_links
        need = min_valid_links - len(kept_links)
        if need > 0 and filtered_links:
            kept_links.extend(filtered_links[:need])
            warnings.append(f"content_check: relaxed filter to keep +{min(len(filtered_links), need)} links")

    need_regen = (
        len(disciplines) < min_disciplines
        or (total_rel > 0 and generic_ratio > max_generic_rel_ratio)
        or len(kept_links) < min_valid_links
        or (edge_cnt > 0 and cross_ratio < min_cross_discipline_edge_ratio)
    )

    reason = "; ".join(warnings) if warnings else ""
    return {"links": kept_links, "warnings": warnings, "need_regen": need_regen, "reason": reason}