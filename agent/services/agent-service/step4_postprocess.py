# step4_postprocess.py
import time
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional, Set


DEFAULT_STEP4_CFG = {
    # ---- 图规模控制 ----
    "max_nodes": 20,
    "max_edges": 30,

    # ---- 置信度阈值 ----
    "min_edge_confidence": 0.55,
    "min_edge_confidence_floor": 0.35,  # 跨域不足时允许降到这个下限

    # ---- 覆盖与跨域目标 ----
    # 注意：domains 统计按“最终保留的子图节点”计算（不是输入 nodes 的全集）
    "min_domains_covered": 4,

    # cross-domain 统计有两种口径：
    # - all：只要 source.field != target.field 就算跨域
    # - highlight：还要 relation_type 在 cross_domain_relation_types 里
    "min_cross_domain_edges_all": 4,
    "min_cross_domain_edges_highlight": 2,
    "cross_domain_mode": "all",  # "all" 或 "highlight"：用于打 tag/高亮优先策略

    # ---- 远亲/桥梁优先保留（如果 tags 里有）----
    "keep_far_edge_tag": "远亲概念",
    "keep_bridge_tag": "桥梁链路",

    # ---- 哪些关系类型算“跨域亮点边” ----
    "cross_domain_relation_types": ["类比关联", "数学关联", "相对/对比", "因果/机制", "应用关联"],

    # ---- 更严格解释性要求 ----
    # 哪些类型必须有 reasoning_chain / bridge_concepts / sources 之一
    "require_reasoning_for_types": ["类比关联"],
    # 若不满足上面要求，但 evidence 够长是否允许放行（建议 False，避免“空洞类比”）
    "allow_evidence_only_for_reasoning_required": False,

    # ---- evidence/reasoning 质量门槛 ----
    "min_evidence_len": 8,              # evidence 最少长度（清洗后）
    "max_evidence_len": 120,            # evidence 最长
    "min_reasoning_steps": 2,           # reasoning_chain 最少步数
    "max_reasoning_steps": 4,           # reasoning_chain 最多步数
    "max_reasoning_step_len": 40,       # 每步最长

    # ---- field 枚举（必须和 Step1/2/3 统一）----
    "allowed_fields": ["核心", "数学", "物理", "计算机/AI", "生物/神经科学", "社会科学/经济学"],

    # ---- relation_type 枚举（必须和 Step3 统一）----
    "allowed_relation_types": ["直接关联", "类比关联", "数学关联", "先修依赖", "应用关联", "因果/机制", "相对/对比", "其他"],

    # ---- 去重粒度 ----
    # "coarse"： (source,target,relation_type)
    # "fine"  ： (source,target,relation_type,relation)
    "dedup_granularity": "coarse",

    # ---- 输出安全 ----
    "clean_edge_relation_max_len": 16,  # 你 Step3 里 relation <=16，这里也同步裁剪
    "clean_edge_relation_fallback_max_len": 32,  # 若历史数据更长，用这个兜底
    "drop_unknown_edge_fields": False,  # True 时会剥离除白名单外的 edge 字段（更严格）
}


# -------------------------
# util
# -------------------------
def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _node_id(n: Dict[str, Any]) -> str:
    return str(n.get("id", "")).strip()


def _clean_str_one_line(s: Any, max_len: Optional[int] = None) -> str:
    txt = str(s or "").strip()
    txt = txt.replace("\r", " ").replace("\n", " ")
    txt = re.sub(r"\s+", " ", txt).strip()
    if max_len is not None:
        txt = txt[:max_len]
    return txt


def _edge_key(e: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[str, str, str, str]:
    # 去重键：可 coarse / fine
    s = str(e.get("source", "")).strip()
    t = str(e.get("target", "")).strip()
    rt = str(e.get("relation_type", "")).strip()
    rel = str(e.get("relation", "")).strip()
    if cfg.get("dedup_granularity") == "fine":
        return (s, t, rt, rel)
    return (s, t, rt, "")


def _is_tagged(e: Dict[str, Any], tag: str) -> bool:
    tags = e.get("tags") or []
    return isinstance(tags, list) and tag in tags


def _ensure_tag(e: Dict[str, Any], tag: str) -> None:
    tags = e.get("tags")
    if tags is None:
        e["tags"] = [tag]
        return
    if isinstance(tags, list) and tag not in tags:
        tags.append(tag)


def _node_field_map(nodes: List[Dict[str, Any]]) -> Dict[str, str]:
    return {_node_id(n): str(n.get("field", "")).strip() for n in nodes if _node_id(n)}


def _find_core_id(nodes: List[Dict[str, Any]]) -> Optional[str]:
    core = [n for n in nodes if str(n.get("type", "")).strip() == "core"]
    if core:
        return _node_id(core[0]) or None
    if not nodes:
        return None
    nodes_sorted = sorted(nodes, key=lambda x: _safe_float(x.get("importance", 0.0), 0.0), reverse=True)
    return _node_id(nodes_sorted[0]) or _node_id(nodes[0]) or None


def _allowed_domain_set(cfg: Dict[str, Any]) -> Set[str]:
    return set(cfg["allowed_fields"]) - {"核心"}


def _collect_domains_from_nodes(nodes: List[Dict[str, Any]], cfg: Dict[str, Any]) -> Set[str]:
    allowed = _allowed_domain_set(cfg)
    s: Set[str] = set()
    for n in nodes:
        f = str(n.get("field", "")).strip()
        if f in allowed:
            s.add(f)
    return s


def _collect_domains_from_edge_induced_subgraph(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    core_id: Optional[str],
) -> Set[str]:
    """按最终边诱导出的节点子图统计覆盖域，更贴近“图可用性”"""
    id2field = _node_field_map(nodes)
    keep_ids: Set[str] = set()
    for e in edges:
        keep_ids.add(str(e.get("source", "")).strip())
        keep_ids.add(str(e.get("target", "")).strip())
    if core_id:
        keep_ids.add(core_id)

    allowed = _allowed_domain_set(cfg)
    domains: Set[str] = set()
    for nid in keep_ids:
        f = id2field.get(nid, "")
        if f in allowed:
            domains.add(f)
    return domains


def _is_cross_domain_edge_all(e: Dict[str, Any], id2field: Dict[str, str]) -> bool:
    s = str(e.get("source", "")).strip()
    t = str(e.get("target", "")).strip()
    fs = id2field.get(s, "")
    ft = id2field.get(t, "")
    return bool(fs and ft and fs != ft)


def _is_cross_domain_edge_highlight(e: Dict[str, Any], id2field: Dict[str, str], cfg: Dict[str, Any]) -> bool:
    if not _is_cross_domain_edge_all(e, id2field):
        return False
    rt = str(e.get("relation_type", "")).strip()
    return rt in set(cfg["cross_domain_relation_types"])


def _count_cross(edges: List[Dict[str, Any]], id2field: Dict[str, str], cfg: Dict[str, Any]) -> Tuple[int, int]:
    """返回 (cross_all, cross_highlight)"""
    cross_all = 0
    cross_hi = 0
    for e in edges:
        if _is_cross_domain_edge_all(e, id2field):
            cross_all += 1
            if _is_cross_domain_edge_highlight(e, id2field, cfg):
                cross_hi += 1
    return cross_all, cross_hi


def _has_reasoning_sources_bridge(e: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
    rc = e.get("reasoning_chain")
    src = e.get("sources")
    bc = e.get("bridge_concepts")

    has_rc = isinstance(rc, list) and len([x for x in rc if str(x).strip()]) >= int(cfg["min_reasoning_steps"])
    has_src = isinstance(src, list) and len([x for x in src if str(x).strip()]) > 0
    has_bc = isinstance(bc, list) and len([x for x in bc if str(x).strip()]) > 0
    return has_rc or has_src or has_bc


def _edge_valid_structure(e: Dict[str, Any], node_ids: Set[str], cfg: Dict[str, Any]) -> bool:
    s = str(e.get("source", "")).strip()
    t = str(e.get("target", "")).strip()
    if not s or not t or s == t:
        return False
    if s not in node_ids or t not in node_ids:
        return False

    rt = str(e.get("relation_type", "")).strip()
    if rt not in set(cfg["allowed_relation_types"]):
        return False

    rel = _clean_str_one_line(e.get("relation", ""), cfg.get("clean_edge_relation_fallback_max_len", 32))
    if not rel:
        return False

    ev = _clean_str_one_line(e.get("evidence", ""), cfg.get("max_evidence_len", 120))
    if len(ev) < int(cfg.get("min_evidence_len", 8)):
        return False

    direction = str(e.get("direction", "")).strip()
    if direction not in {"directed", "undirected"}:
        return False

    conf = _safe_float(e.get("confidence", 0.0), 0.0)
    if conf <= 0.0:
        # 允许 0.0 吗？一般不该
        return False
    return True


def _normalize_edge_fields_inplace(e: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    # 清理关键字符串字段
    e["relation"] = _clean_str_one_line(e.get("relation", ""), cfg.get("clean_edge_relation_max_len", 16))
    e["evidence"] = _clean_str_one_line(e.get("evidence", ""), cfg.get("max_evidence_len", 120))

    # 清理 reasoning_chain / bridge_concepts（可选）
    if isinstance(e.get("reasoning_chain"), list):
        cleaned_steps = []
        for x in e["reasoning_chain"]:
            step = _clean_str_one_line(x, cfg.get("max_reasoning_step_len", 40))
            if step:
                cleaned_steps.append(step)
        e["reasoning_chain"] = cleaned_steps[: cfg.get("max_reasoning_steps", 4)]

    if isinstance(e.get("bridge_concepts"), list):
        e["bridge_concepts"] = [str(x).strip() for x in e["bridge_concepts"] if str(x).strip()]

    # 置信度强制转 float
    if "confidence" in e:
        e["confidence"] = _safe_float(e.get("confidence", 0.0), 0.0)

    # 可选：剥离不认识字段（更严格、对 Step3 输出很有用）
    if cfg.get("drop_unknown_edge_fields", False):
        allowed = {"source", "target", "relation", "relation_type", "confidence", "evidence", "direction",
                   "reasoning_chain", "bridge_concepts", "tags", "sources"}
        for k in list(e.keys()):
            if k not in allowed:
                del e[k]


def _prune_edges_keep_highlights(
    edges: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    max_edges: int,
) -> List[Dict[str, Any]]:
    """裁剪策略：far/bridge > cross-highlight > cross-all > normal，按 confidence 排序"""
    id2field = _node_field_map(nodes)

    far = []
    bridge = []
    cross_hi = []
    cross_all = []
    normal = []

    for e in edges:
        if _is_tagged(e, cfg["keep_far_edge_tag"]):
            far.append(e)
        elif _is_tagged(e, cfg["keep_bridge_tag"]):
            bridge.append(e)
        elif _is_cross_domain_edge_highlight(e, id2field, cfg):
            cross_hi.append(e)
        elif _is_cross_domain_edge_all(e, id2field):
            cross_all.append(e)
        else:
            normal.append(e)

    key = lambda x: _safe_float(x.get("confidence", 0.0), 0.0)
    for bucket in (far, bridge, cross_hi, cross_all, normal):
        bucket.sort(key=key, reverse=True)

    out = far + bridge + cross_hi + cross_all
    if len(out) < max_edges:
        out.extend(normal[: max_edges - len(out)])
    return out[:max_edges]


def _prune_nodes_by_importance(nodes: List[Dict[str, Any]], keep_ids: Set[str], max_nodes: int) -> List[Dict[str, Any]]:
    pinned = [n for n in nodes if _node_id(n) in keep_ids]
    others = [n for n in nodes if _node_id(n) not in keep_ids]

    others.sort(key=lambda x: _safe_float(x.get("importance", 0.0), 0.0), reverse=True)

    out = pinned + others
    seen = set()
    uniq = []
    for n in out:
        nid = _node_id(n)
        if nid and nid not in seen:
            seen.add(nid)
            uniq.append(n)
    return uniq[:max_nodes]


# -------------------------
# Step4 main
# -------------------------
def step4_postprocess_graph(
    *,
    meta: Optional[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Step4 = 过滤、修正、降级、保证可用（工程保证层）
    返回：{"meta":..., "nodes":..., "edges":...}
    """
    t0 = time.time()
    cfg = {**DEFAULT_STEP4_CFG, **(cfg or {})}
    removed = defaultdict(int)
    notes: List[str] = []

    # ---- 0) nodes 基础合法性：field 枚举校验（不合法剔除）----
    allowed_fields = set(cfg["allowed_fields"])
    nodes0 = []
    for n in nodes:
        nid = _node_id(n)
        if not nid:
            removed["node_missing_id"] += 1
            continue
        f = str(n.get("field", "")).strip()
        if f not in allowed_fields:
            removed["node_bad_field"] += 1
            continue
        nodes0.append(n)
    nodes = nodes0

    # ---- 1) nodes 去重：保留 importance 更高版本 ----
    best_nodes: Dict[str, Dict[str, Any]] = {}
    for n in nodes:
        nid = _node_id(n)
        if nid in best_nodes:
            old = best_nodes[nid]
            if _safe_float(n.get("importance", 0.0), 0.0) > _safe_float(old.get("importance", 0.0), 0.0):
                best_nodes[nid] = n
            removed["node_duplicate"] += 1
        else:
            best_nodes[nid] = n

    nodes = list(best_nodes.values())
    node_ids: Set[str] = set(best_nodes.keys())
    id2field = _node_field_map(nodes)
    core_id = _find_core_id(nodes)

    # ---- 2) edges 结构合法 + 清理字段 ----
    edges_valid: List[Dict[str, Any]] = []
    for e in edges:
        if not isinstance(e, dict):
            removed["edge_not_object"] += 1
            continue

        _normalize_edge_fields_inplace(e, cfg)

        if not _edge_valid_structure(e, node_ids, cfg):
            removed["edge_invalid_structure"] += 1
            continue

        # 约束 reasoning_chain：若存在但太短，也视作不存在（避免“装样子”）
        if isinstance(e.get("reasoning_chain"), list):
            rc = [x for x in e["reasoning_chain"] if str(x).strip()]
            if len(rc) < int(cfg["min_reasoning_steps"]):
                e.pop("reasoning_chain", None)

        edges_valid.append(e)

    edges = edges_valid

    # ---- 3) edges 去重：按 confidence 保留更高者 ----
    best_edges: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for e in edges:
        k = _edge_key(e, cfg)
        if k in best_edges:
            if _safe_float(e.get("confidence", 0.0), 0.0) > _safe_float(best_edges[k].get("confidence", 0.0), 0.0):
                best_edges[k] = e
            removed["edge_duplicate"] += 1
        else:
            best_edges[k] = e
    edges = list(best_edges.values())

    # ---- 4) 解释性规则：某些类型必须 reasoning/sources/bridge ----
    req_types = set(cfg["require_reasoning_for_types"])
    edges2: List[Dict[str, Any]] = []
    for e in edges:
        rt = str(e.get("relation_type", "")).strip()
        if rt in req_types:
            ok = _has_reasoning_sources_bridge(e, cfg)
            if not ok and cfg.get("allow_evidence_only_for_reasoning_required", False):
                # 允许 evidence-only 放行（不推荐）
                ok = len(_clean_str_one_line(e.get("evidence", ""), None)) >= max(16, int(cfg.get("min_evidence_len", 8)))
            if not ok:
                removed["edge_missing_reasoning"] += 1
                continue
        edges2.append(e)
    edges = edges2

    # ---- 5) 自动打 tag：跨域连接、无向关系、核心相关 ----
    # cross_domain_mode="highlight" 时，只有亮点跨域才打“跨域连接”
    cross_mode = str(cfg.get("cross_domain_mode", "all")).strip().lower()
    for e in edges:
        is_cross_all = _is_cross_domain_edge_all(e, id2field)
        is_cross_hi = _is_cross_domain_edge_highlight(e, id2field, cfg)

        if cross_mode == "highlight":
            if is_cross_hi:
                _ensure_tag(e, "跨域连接")
        else:
            if is_cross_all:
                _ensure_tag(e, "跨域连接")

        if str(e.get("direction", "")).strip() == "undirected":
            _ensure_tag(e, "无向关系")

        if core_id and (e["source"] == core_id or e["target"] == core_id):
            _ensure_tag(e, "核心相关")

    # ---- 6) 置信度过滤：远亲/桥梁/跨域可放宽 ----
    def filter_by_threshold(th: float) -> List[Dict[str, Any]]:
        out = []
        for e in edges:
            conf = _safe_float(e.get("confidence", 0.0), 0.0)
            keep = conf >= th
            if not keep and (
                _is_tagged(e, cfg["keep_far_edge_tag"])
                or _is_tagged(e, cfg["keep_bridge_tag"])
                or _is_tagged(e, "跨域连接")
            ):
                keep = True
            if keep:
                out.append(e)
        return out

    min_conf = float(cfg["min_edge_confidence"])
    edges = filter_by_threshold(min_conf)

    # ---- 7) 跨域/覆盖不足：自动“降阈值救图” ----
    # 注意：domains_covered 按“边诱导子图”统计；降阈值只会影响 edges，从而影响该统计
    def stats_for(edges_list: List[Dict[str, Any]]) -> Tuple[Set[str], int, int]:
        dom = _collect_domains_from_edge_induced_subgraph(nodes, edges_list, cfg, core_id)
        cross_all, cross_hi = _count_cross(edges_list, id2field, cfg)
        return dom, cross_all, cross_hi

    domains_covered, cross_all_cnt, cross_hi_cnt = stats_for(edges)

    need_domains = int(cfg["min_domains_covered"])
    need_cross_all = int(cfg["min_cross_domain_edges_all"])
    need_cross_hi = int(cfg["min_cross_domain_edges_highlight"])

    if len(domains_covered) < need_domains or cross_all_cnt < need_cross_all or cross_hi_cnt < need_cross_hi:
        th = min_conf
        floor = float(cfg["min_edge_confidence_floor"])

        best_edges_try = edges
        best_dom = domains_covered
        best_cross_all = cross_all_cnt
        best_cross_hi = cross_hi_cnt
        best_th = th

        while th > floor:
            th = max(floor, th - 0.05)
            edges_try = filter_by_threshold(th)
            dom_try, ca_try, ch_try = stats_for(edges_try)

            # 选择“更满足约束”的结果：优先域覆盖，其次 cross_all，其次 cross_hi，其次边数少（更干净）
            def score(dom: Set[str], ca: int, ch: int, n: int) -> Tuple[int, int, int, int]:
                return (len(dom), ca, ch, -n)

            if score(dom_try, ca_try, ch_try, len(edges_try)) > score(best_dom, best_cross_all, best_cross_hi, len(best_edges_try)):
                best_edges_try = edges_try
                best_dom = dom_try
                best_cross_all = ca_try
                best_cross_hi = ch_try
                best_th = th

            if len(dom_try) >= need_domains and ca_try >= need_cross_all and ch_try >= need_cross_hi:
                # 已满足，提前停止
                best_edges_try = edges_try
                best_dom = dom_try
                best_cross_all = ca_try
                best_cross_hi = ch_try
                best_th = th
                break

        edges = best_edges_try
        domains_covered = best_dom
        cross_all_cnt = best_cross_all
        cross_hi_cnt = best_cross_hi

        notes.append(f"为满足覆盖/跨域约束，min_edge_confidence 自动调整为 {best_th:.2f}。")

    # ---- 8) 边数量裁剪：亮点优先 ----
    if len(edges) > int(cfg["max_edges"]):
        notes.append(f"edges 超过上限 {cfg['max_edges']}，按亮点优先策略裁剪。")
        edges = _prune_edges_keep_highlights(edges, nodes, cfg, int(cfg["max_edges"]))
        # 裁剪后重新统计
        domains_covered, cross_all_cnt, cross_hi_cnt = stats_for(edges)

    # ---- 9) 点数量裁剪：优先保留被边引用 + 核心 ----
    keep_ids: Set[str] = set()
    for e in edges:
        keep_ids.add(str(e["source"]))
        keep_ids.add(str(e["target"]))
    if core_id:
        keep_ids.add(core_id)

    if len(nodes) > int(cfg["max_nodes"]):
        notes.append(f"nodes 超过上限 {cfg['max_nodes']}，按 importance 裁剪。")
        nodes = _prune_nodes_by_importance(nodes, keep_ids, int(cfg["max_nodes"]))
        node_ids2 = set(_node_id(n) for n in nodes if _node_id(n))
        edges = [e for e in edges if e["source"] in node_ids2 and e["target"] in node_ids2]
        # 重新统计
        id2field = _node_field_map(nodes)
        core_id = _find_core_id(nodes)
        domains_covered = _collect_domains_from_edge_induced_subgraph(nodes, edges, cfg, core_id)
        cross_all_cnt, cross_hi_cnt = _count_cross(edges, id2field, cfg)

    # ---- 10) meta.stats（补充两种跨域计数） ----
    meta_out = dict(meta or {})
    meta_out.setdefault("stats", {})
    meta_out["stats"]["num_nodes"] = len(nodes)
    meta_out["stats"]["num_edges"] = len(edges)
    meta_out["stats"]["num_domains_covered"] = len(domains_covered)
    meta_out["stats"]["num_cross_domain_edges"] = cross_all_cnt  # 兼容旧字段：默认用 all
    meta_out["stats"]["num_cross_domain_edges_all"] = cross_all_cnt
    meta_out["stats"]["num_cross_domain_edges_highlight"] = cross_hi_cnt

    cost_ms = int((time.time() - t0) * 1000)
    summary_removed = ", ".join([f"{k}={v}" for k, v in removed.items() if v > 0])
    note_text = f"Step4 QC done ({cost_ms}ms)."
    if summary_removed:
        note_text += f" Removed: {summary_removed}."
    if notes:
        note_text += " " + "；".join(notes)

    meta_out["notes"] = (str(meta_out.get("notes", "")).strip() + " | " + note_text).strip(" |")

    return {"meta": meta_out, "nodes": nodes, "edges": edges}
