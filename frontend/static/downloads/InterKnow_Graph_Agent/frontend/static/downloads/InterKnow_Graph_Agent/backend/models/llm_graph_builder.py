from __future__ import annotations
import os
from typing import Any, Dict, Optional
from volcenginesdkarkruntime import Ark
from .lib.prompts import build_prompt, stronger_prompt_for_regen, force_json_repair_prompt
from .lib.ark_io import extract_text_from_ark_response, extract_token_detail
from .lib.sanitize import (
    extract_json,
    validate_and_fix,
    prune_isolated_nodes,
    compute_node_values_scaled,
)
from .lib.quality import content_check

from config import API_KEY, MODEL_ID, BASE_URL

# 规模限制
MAX_NODES = 30
MAX_LINKS = 60

# 内容校验参数
MIN_DISCIPLINES = 3
MIN_VALID_LINKS = 6           # 减少断开
MIN_RELATION_LEN = 4
MAX_RELATION_LEN = 40
MAX_GENERIC_REL_RATIO = 0.55  # 略放宽，减少误杀
MIN_CROSS_DISCIPLINE_EDGE_RATIO = 0.25  # 略放宽，减少误杀

def build_knowledge_graph(concept: str) -> Dict[str, Any]:
    concept = (concept or "").strip()
    if not concept:
        return {"nodes": [], "links": [], "warnings": ["empty concept"], "tokens": 0}

    if not API_KEY or not MODEL_ID:
        return {"nodes": [], "links": [], "warnings": ["missing VOLC_ARK_API_KEY or VOLC_ARK_MODEL"], "tokens": 0}

    client = Ark(base_url=BASE_URL, api_key=API_KEY)

    total_tokens = 0
    model_text: Optional[str] = None

    def _call_once(prompt_text: str) -> str:
        nonlocal total_tokens
        resp = client.responses.create(
            model=MODEL_ID,
            input=[{"role": "user", "content": [{"type": "input_text", "text": prompt_text}]}],
        )
        total_tokens += int(extract_token_detail(resp).get("total_tokens", 0))
        return extract_text_from_ark_response(resp)

    def _finalize(graph: Dict[str, Any], warnings_extra: Optional[list] = None) -> Dict[str, Any]:
        # 补默认 description
        for n in graph.get("nodes", []):
            if not (n.get("description") or "").strip():
                n["description"] = f"{n.get('name','')}：与“{concept}”相关的概念。"

        for e in graph.get("links", []):
            if not (e.get("description") or "").strip():
                e["description"] = f"{e.get('relation','')}：描述 {e.get('source')} → {e.get('target')} 与“{concept}”的关联。"

        # 剪掉孤立节点，减少前端“飘点”
        nodes2, pruned = prune_isolated_nodes(graph["nodes"], graph["links"], concept)
        graph["nodes"] = nodes2
        if pruned > 0:
            graph.setdefault("warnings", []).append(f"sanitize: pruned {pruned} isolated nodes")

        # 放大 value
        values = compute_node_values_scaled(graph["nodes"], graph["links"])
        for n in graph["nodes"]:
            n["value"] = values.get(n["id"], 10)

        # 合并 warnings
        if warnings_extra:
            graph.setdefault("warnings", []).extend(warnings_extra)

        # 顶层 tokens
        graph["tokens"] = int(total_tokens)
        return graph

    try:
        # 1) 第一次生成
        model_text = _call_once(build_prompt(concept, MAX_NODES, MAX_LINKS))
        graph_raw = extract_json(model_text)
        graph = validate_and_fix(graph_raw, MAX_NODES, MAX_LINKS)

        # 2) 内容层校验（过滤/统计/放宽）
        cc = content_check(
            graph["nodes"],
            graph["links"],
            min_disciplines=MIN_DISCIPLINES,
            min_valid_links=MIN_VALID_LINKS,
            min_relation_len=MIN_RELATION_LEN,
            max_relation_len=MAX_RELATION_LEN,
            max_generic_rel_ratio=MAX_GENERIC_REL_RATIO,
            min_cross_discipline_edge_ratio=MIN_CROSS_DISCIPLINE_EDGE_RATIO,
        )
        graph["links"] = cc["links"]
        if cc["warnings"]:
            graph["warnings"] = cc["warnings"]

        # 3) 若判定需要 regen：再生成一次（更强约束）
        if cc["need_regen"]:
            prompt2 = stronger_prompt_for_regen(
                concept, cc["reason"] or "content_check_failed",
                min_disciplines=MIN_DISCIPLINES,
                max_nodes=MAX_NODES,
                max_links=MAX_LINKS
            )
            text2 = _call_once(prompt2)
            raw2 = extract_json(text2)
            graph2 = validate_and_fix(raw2, MAX_NODES, MAX_LINKS)

            cc2 = content_check(
                graph2["nodes"],
                graph2["links"],
                min_disciplines=MIN_DISCIPLINES,
                min_valid_links=MIN_VALID_LINKS,
                min_relation_len=MIN_RELATION_LEN,
                max_relation_len=MAX_RELATION_LEN,
                max_generic_rel_ratio=MAX_GENERIC_REL_RATIO,
                min_cross_discipline_edge_ratio=MIN_CROSS_DISCIPLINE_EDGE_RATIO,
            )
            graph2["links"] = cc2["links"]
            if cc2["warnings"]:
                graph2["warnings"] = cc2["warnings"]

            # 简单评分：优先有效边更多，其次学科覆盖更高
            def _score(g: Dict[str, Any]) -> int:
                dset = {n.get("discipline") for n in g.get("nodes", []) if isinstance(n.get("discipline"), str)}
                return (len(g.get("links", [])) * 10) + len(dset)

            graph = graph2 if _score(graph2) >= _score(graph) else graph

        if not graph.get("nodes"):
            return {"nodes": [], "links": [], "warnings": ["no valid nodes after validation"], "tokens": total_tokens}

        return _finalize(graph)

    except Exception as e1:
        # JSON 结构失败：repair 一次
        if not model_text or not model_text.strip():
            return {"nodes": [], "links": [], "warnings": [f"llm_output_empty_or_unreadable: {type(e1).__name__}: {e1}"], "tokens": total_tokens}

        try:
            repaired = _call_once(force_json_repair_prompt(model_text, concept, MAX_NODES, MAX_LINKS))
            raw2 = extract_json(repaired)
            graph2 = validate_and_fix(raw2, MAX_NODES, MAX_LINKS)

            cc2 = content_check(
                graph2["nodes"],
                graph2["links"],
                min_disciplines=MIN_DISCIPLINES,
                min_valid_links=MIN_VALID_LINKS,
                min_relation_len=MIN_RELATION_LEN,
                max_relation_len=MAX_RELATION_LEN,
                max_generic_rel_ratio=MAX_GENERIC_REL_RATIO,
                min_cross_discipline_edge_ratio=MIN_CROSS_DISCIPLINE_EDGE_RATIO,
            )
            graph2["links"] = cc2["links"]
            if cc2["warnings"]:
                graph2["warnings"] = cc2["warnings"]

            if not graph2.get("nodes"):
                return {"nodes": [], "links": [], "warnings": ["no valid nodes after repair"], "tokens": total_tokens}

            return _finalize(graph2)

        except Exception as e2:
            return {"nodes": [], "links": [], "warnings": [f"llm_call_failed: {type(e2).__name__}: {e2}"], "tokens": total_tokens}

if __name__ == "__main__":
    print(build_knowledge_graph("熵"))