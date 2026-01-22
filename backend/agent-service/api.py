# services/agent-service/api.py
import os
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from llm_client import LLMClient
from agent_pipeline import (
    step0_validate_and_normalize,
    step1_generate_candidates,
    step2_enrich_nodes,
    merge_step2_into_nodes,
    step3_generate_edges,
)

from step4_postprocess import step4_postprocess_graph


app = FastAPI(
    title="Knowledge Graph Agent Service",
    version="0.1.0",
    description="跨学科知识图谱智能体服务：输入概念词，输出 GraphJSON（meta/nodes/edges）。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    concept: str = Field(..., min_length=1, max_length=80, description="核心概念词（中文为主）")
    debug: bool = Field(False, description="是否返回调试信息（精简版）")
    trace_id: Optional[str] = Field(None, description="链路追踪ID（不传则自动生成）")
    cfg: Optional[Dict[str, Any]] = Field(None, description="可选：Step4配置覆盖（如max_edges等）")


class GenerateResponse(BaseModel):
    ok: bool
    trace_id: str
    elapsed_ms: int
    graph: Optional[Dict[str, Any]] = None
    debug: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None  # {"stage": "...", "message": "..."}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/graph/build", response_model=GenerateResponse)
def build_graph(req: GenerateRequest):
    t0 = time.time()
    trace_id = (req.trace_id or str(uuid.uuid4())).strip()

    concept = (req.concept or "").strip()
    if not concept:
        raise HTTPException(status_code=400, detail="concept 不能为空")

    client = LLMClient()

    def _elapsed_ms() -> int:
        return int((time.time() - t0) * 1000)

    try:
        # Step0
        step0 = step0_validate_and_normalize(concept, client)
        if not step0.get("valid", False):
            # 这种属于输入不可用：400
            raise HTTPException(status_code=400, detail=f"Step0 invalid: {step0.get('reason', '')}")

        # Step1
        step1 = step1_generate_candidates(step0, client)

        # Step2
        step2 = step2_enrich_nodes(step1, client)

        # Merge nodes
        merged_nodes = merge_step2_into_nodes(step1["nodes"], step2["nodes"])

        # Step3
        step3 = step3_generate_edges(merged_nodes, client)

        # Step4：工程后处理（你贴的函数签名是 meta/nodes/edges/cfg）
        meta = {"concept": concept, "trace_id": trace_id}
        final_graph = step4_postprocess_graph(
            meta=meta,
            nodes=merged_nodes,
            edges=step3["edges"],
            cfg=req.cfg,
        )

        debug_payload = None
        if req.debug:
            # debug 只给精简信息，避免 response 过大
            debug_payload = {
                "step0_reason": step0.get("reason", ""),
                "num_nodes_step1": len(step1.get("nodes", []) or []),
                "num_nodes_merged": len(merged_nodes),
                "num_edges_step3": len(step3.get("edges", []) or []),
                "step4_notes": (final_graph.get("meta", {}) or {}).get("notes", ""),
            }

        return GenerateResponse(
            ok=True,
            trace_id=trace_id,
            elapsed_ms=_elapsed_ms(),
            graph=final_graph,
            debug=debug_payload,
            error=None,
        )

    except HTTPException as he:
        return GenerateResponse(
            ok=False,
            trace_id=trace_id,
            elapsed_ms=_elapsed_ms(),
            graph=None,
            debug=None,
            error={"stage": "http", "message": str(he.detail)},
        )

    except Exception as e:
        # 统一 500
        return GenerateResponse(
            ok=False,
            trace_id=trace_id,
            elapsed_ms=_elapsed_ms(),
            graph=None,
            debug=None,
            error={"stage": "internal", "message": str(e)},
        )
