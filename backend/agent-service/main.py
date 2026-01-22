import json
import os
from llm_client import LLMClient
from agent_pipeline import (
    step0_validate_and_normalize,
    step1_generate_candidates,
    step2_enrich_nodes,
    merge_step2_into_nodes,
    step3_generate_edges,
)
from step4_postprocess import step4_postprocess_graph  # ✅ 新增


def _dump(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    concept = input("请输入概念词：").strip()
    client = LLMClient()

    # Step0
    step0 = step0_validate_and_normalize(concept, client)
    print("\n[Step0 Result]\n" + json.dumps(step0, ensure_ascii=False, indent=2))
    if not step0.get("valid"):
        raise SystemExit("Step0 invalid: " + step0.get("reason", ""))

    # Step1
    step1 = step1_generate_candidates(step0, client)
    print("\n[Step1 Nodes]\n" + json.dumps(step1, ensure_ascii=False, indent=2))

    # Step2
    step2 = step2_enrich_nodes(step1, client)
    print("\n[Step2 Enriched Fields]\n" + json.dumps(step2, ensure_ascii=False, indent=2))

    # Merge Step2 -> Step1 nodes
    merged_nodes = merge_step2_into_nodes(step1["nodes"], step2["nodes"])
    print("\n[Nodes Merged]\n" + json.dumps({"nodes": merged_nodes}, ensure_ascii=False, indent=2))

    # Step3
    step3 = step3_generate_edges(merged_nodes, client)
    print("\n[Step3 Edges RAW]\n" + json.dumps(step3, ensure_ascii=False, indent=2))

    # Step4 ✅（过滤、修正、降级、保证可用）
    final_graph = step4_postprocess_graph(
        meta={"concept": concept},
        nodes=merged_nodes,
        edges=step3["edges"],
        cfg=None,  # 或者传你自己的 cfg dict
    )
    print("\n[Step4 Final Graph]\n" + json.dumps(final_graph, ensure_ascii=False, indent=2))

    # （可选）落盘方便调试/写报告
    _dump("outputs/step1_nodes.json", step1)
    _dump("outputs/step2_nodes_enriched.json", step2)
    _dump("outputs/step3_edges_raw.json", step3)
    _dump("outputs/step4_graph_final.json", final_graph)
