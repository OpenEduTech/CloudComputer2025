from __future__ import annotations

import asyncio
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# 引入 Shared Models
from common.models import (
    APIResponse, CancelTaskResult, ClassifyRequest, ClassifyResult,
    Pagination, PlanRequest, PlanResult, PlanDiscipline,
    SearchResultsResponseData, SearchStartRequest, SearchStartResult,
    SearchStatusData, SearchSummary, Chunk,
    GraphResponse, QARequest, QAResponse # 引入新模型
)

# 引入 Services
from search_agent.service import SearchService
from search_agent.graph import search_graph
from knowledge_engine.service import KnowledgeService # 引入 KE Service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("central-agent")

app = FastAPI(title="Central Agent", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 实例化 Services
search_service = SearchService()
knowledge_service = KnowledgeService()

# 任务状态存储
TASKS: Dict[str, Dict[str, Any]] = {}

@app.get("/api/health")
async def health() -> APIResponse:
    return APIResponse(data={"status": "ok", "service": "central-agent"})

# ========== 1. Search Agent 接口 ==========

@app.post("/api/search/classify")
async def classify(req: ClassifyRequest) -> APIResponse:
    data = await search_service.classify(req.concept, req.max_disciplines, req.min_relevance)
    return APIResponse(data=ClassifyResult(**data))

@app.post("/api/search/plan")
async def plan(req: PlanRequest) -> APIResponse:
    raw = await search_service.classify(req.concept, req.max_disciplines, req.min_relevance)
    # ... (保持之前的 Plan 逻辑，省略重复代码以节省篇幅，逻辑同前) ...
    # 简单实现供运行
    disciplines = raw.get("disciplines", [])
    data = PlanResult(
        concept=req.concept,
        primary_discipline=raw.get("primary_discipline", "综合"),
        disciplines=[PlanDiscipline(**d, is_default_selected=True) for d in disciplines],
        suggested_additions=[]
    )
    return APIResponse(data=data)

@app.post("/api/search/start")
async def start(req: SearchStartRequest) -> APIResponse:
    task_id = f"task-{uuid.uuid4()}"
    
    # 1. 初始化任务状态
    TASKS[task_id] = {
        "task_id": task_id,
        "concept": req.concept,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "progress": {"overall": 0, "current_stage": "pending", "stages": {}},
        "partial": {"total_chunks_found": 0, "validated_chunks": 0},
        "result_chunks": [],
        "cancelled": False,
        "error": None
    }

    # 2. 准备初始状态
    # 注意：确保这里的数据转换没有报错
    try:
        initial_state = {
            "task_id": task_id,
            "concept": req.concept,
            "disciplines": [d.model_dump() for d in req.disciplines],
            "search_config": req.search_config.model_dump(),
            "raw_search_items": [],
            "chunks": [],
            "graph_status": "pending"
        }
    except Exception as e:
        logger.error(f"Failed to prepare initial state: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request data: {str(e)}")

    # 3. 定义后台任务 (增加全包裹 Try-Except)
    async def run_langgraph_task():
        logger.info(f"🚀 Background task started for {task_id}")  # [关键日志1] 证明任务启动了
        
        try:
            # 获取引用
            task_data = TASKS[task_id]
            
            # 更新状态为 processing
            task_data["status"] = "processing"
            task_data["progress"]["current_stage"] = "starting"
            task_data["updated_at"] = datetime.utcnow()
            
            logger.info(f"Set status to processing for {task_id}") # [关键日志2] 证明状态更新代码执行了

            # 定义回调
            def status_callback(stage: str, overall: int, extra: dict | None = None):
                task_data["progress"]["current_stage"] = stage
                task_data["progress"]["overall"] = overall
                task_data["progress"]["stages"][stage] = "in_progress"
                
                # 更新已完成阶段的状态
                stages_order = ["search", "validation", "constructing", "ingesting", "completed"]
                try:
                    curr_idx = stages_order.index(stage)
                    for prev in stages_order[:curr_idx]:
                        task_data["progress"]["stages"][prev] = "completed"
                except ValueError: pass

                if extra and "total" in extra:
                    task_data["partial"]["total_chunks_found"] = extra["total"]
                    
                task_data["updated_at"] = datetime.utcnow()

            def check_cancelled():
                return task_data.get("cancelled", False)

            # 运行 Graph
            logger.info(f"Invoking graph for {task_id}...") # [关键日志3] 开始调用 LangGraph
            
            final_state = await search_graph.ainvoke(
                initial_state, 
                config={"configurable": {"status_callback": status_callback, "cancelled_check": check_cancelled}}
            )
            
            logger.info(f"Graph finished for {task_id}") # [关键日志4] Graph 运行结束

            if check_cancelled():
                task_data["status"] = "cancelled"
            else:
                task_data["status"] = "completed"
                # 安全地获取 chunks，防止 final_state 中没有 chunks 字段
                chunks = final_state.get("chunks", [])
                task_data["result_chunks"] = [c.model_dump() for c in chunks]
                task_data["progress"]["overall"] = 100
                
        except Exception as e:
            # [关键] 捕获所有后台任务的报错
            logger.exception(f"❌ CRITICAL ERROR in background task {task_id}") 
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["error"] = str(e)
        finally:
            TASKS[task_id]["updated_at"] = datetime.utcnow()

    # 4. 提交给 Event Loop
    asyncio.create_task(run_langgraph_task())
    logger.info(f"Task {task_id} scheduled.")

    return APIResponse(
        data=SearchStartResult(
            task_id=task_id,
            status="pending", # 这里返回 pending 是对的，因为后台任务是异步的
            created_at=TASKS[task_id]["created_at"]
        )
    )

@app.get("/api/search/status/{task_id}")
async def status(task_id: str) -> APIResponse:
    t = TASKS.get(task_id)
    if not t: raise HTTPException(404, "Task not found")
    
    return APIResponse(data=SearchStatusData(
        task_id=task_id,
        status=t["status"],
        progress=t["progress"],
        partial_results=t["partial"],
        updated_at=t["updated_at"]
    ))

@app.get("/api/search/results/{task_id}")
async def results(task_id: str, page: int = 1, page_size: int = 20) -> APIResponse:
    t = TASKS.get(task_id)
    if not t or t["status"] != "completed": raise HTTPException(400, "Task not ready")
    
    chunks = t["result_chunks"]
    total = len(chunks)
    start = (page - 1) * page_size
    page_items = chunks[start : start + page_size]
    
    return APIResponse(data=SearchResultsResponseData(
        task_id=task_id,
        concept=t["concept"],
        summary=SearchSummary(total_chunks=total, disciplines_covered=0),
        chunks=page_items,
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=(total+page_size-1)//page_size)
    ))

# ========== 2. Knowledge Engine 接口==========

@app.get("/api/graph/concepts")
async def list_concepts() -> APIResponse:
    """列出所有已构建图谱的概念"""
    concepts = knowledge_service.list_concepts()
    return APIResponse(data={"concepts": concepts})

@app.get("/api/graph/{concept}")
async def get_graph(concept: str) -> APIResponse:
    """获取指定概念的知识图谱"""
    data = knowledge_service.get_graph(concept)
    if not data:
        raise HTTPException(status_code=404, detail=f"Graph for '{concept}' not found")
    return APIResponse(data=GraphResponse(**data))

@app.get("/api/graph/chunk/{chunk_id}")
async def get_chunk(chunk_id: str) -> APIResponse:
    """获取原始文档片段内容"""
    data = knowledge_service.get_chunk(chunk_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Chunk '{chunk_id}' not found")
    return APIResponse(data=data)

@app.post("/api/qa")
async def qa(req: QARequest) -> APIResponse:
    """基于图谱的问答"""
    try:
        answer = await knowledge_service.qa(
            concept=req.concept,
            source=req.source_node,
            target=req.target_node,
            question=req.question
        )
        return APIResponse(data=QAResponse(
            concept=req.concept,
            source_node=req.source_node,
            target_node=req.target_node,
            question=req.question or "默认关系查询",
            answer=answer
        ))
    except Exception as e:
        logger.error(f"QA Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))