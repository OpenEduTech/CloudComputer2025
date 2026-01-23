import asyncio
import logging
import uuid
from typing import Any, Dict, List, TypedDict, Callable, Optional
from langgraph.graph import StateGraph, END

# 引用 Services
from search_agent.service import SearchService, SearchItem, hash_text
from knowledge_engine.service import KnowledgeService
from common.models import Chunk, SourceInfo, ValidationInfo

# 配置日志输出
logger = logging.getLogger("search-graph")
# 强制让 search-graph 的日志显示出来
logging.basicConfig(level=logging.INFO) 

search_service = SearchService()
knowledge_service = KnowledgeService()

# --- State ---
class SearchAgentState(TypedDict):
    task_id: str
    concept: str
    disciplines: List[Dict[str, Any]]
    search_config: Dict[str, Any]
    raw_search_items: List[tuple[str, SearchItem]] 
    validated_meta: Dict[str, Any]
    chunks: List[Chunk]
    graph_status: str

# --- Helpers ---
def get_cb(config: Dict[str, Any]):
    return config.get("configurable", {}).get("status_callback", lambda s, o, e=None: None)

# 
def check_cancelled(config: Dict[str, Any]) -> bool:
    # 1. 获取回调函数
    checker = config.get("configurable", {}).get("cancelled_check", lambda: False)
    # 2. 执行
    return checker()

# --- Nodes ---

async def search_node(state: SearchAgentState, config):
    """搜索节点 """
    logger.info(">>> [Node] Entering Search Node") 
    
    if check_cancelled(config): 
        logger.warning(">>> [Node] Search Cancelled")
        return {}
        
    cb = get_cb(config)
    cb("search", 10, None)
    
    concept = state["concept"]
    disciplines = state["disciplines"]
    max_results = state["search_config"].get("max_results_per_discipline", 10)

    logger.info(f"Concept: {concept}, Disciplines count: {len(disciplines)}")

    if not disciplines:
        logger.error("!!! No disciplines provided, skipping search.")
        return {"raw_search_items": []}

    queries = []
    for d in disciplines:
        name = d["name"]
        kws = d.get("search_keywords") or [name]
        # 限制关键词数量，防止请求过多
        for kw in kws[:3]:
            queries.append((name, f"{concept} {kw}"))
    
    logger.info(f"Generated {len(queries)} queries. Starting parallel search...")

    async def one(discipline: str, q: str):
        if check_cancelled(config): return []
        try:
            # 调用 Service
            items = await search_service.search(q, max_results)
            logger.info(f"   Query '{q}' returned {len(items)} items")
            return items
        except Exception as e:
            logger.error(f"!!! Search FAILED for query '{q}': {e}")
            import traceback
            traceback.print_exc()
            return []

    results_nested = await asyncio.gather(*[one(d, q) for d, q in queries])
    
    flat = []
    seen = set()
    for (disc, _), items in zip(queries, results_nested):
        for it in items:
            key = (it.url or "") + "|" + hash_text(it.content)
            if key in seen: continue
            seen.add(key)
            if len(it.content) < 80: continue
            flat.append((disc, it))
            
    logger.info(f">>> [Node] Search Finished. Total raw items: {len(flat)}")
    cb("aggregation", 55, None)
    return {"raw_search_items": flat}

async def validation_node(state: SearchAgentState, config):
    logger.info(">>> [Node] Entering Validation Node")
    if check_cancelled(config): return {}
    cb = get_cb(config)
    cb("validation", 70, None)
    
    concept = state["concept"]
    items = [it for _, it in state.get("raw_search_items", [])]
    enable_validation = state["search_config"].get("enable_validation", True)
    
    logger.info(f"Validating {len(items)} items. Enable validation: {enable_validation}")

    validated_meta = {}
    if enable_validation and items:
        try:
            validated_meta = await search_service.validate_results(concept, items)
            logger.info(f"Validation complete. Meta count: {len(validated_meta)}")
        except Exception as e:
            logger.error(f"!!! Validation FAILED: {e}")

    return {"validated_meta": validated_meta}

async def construct_chunks_node(state: SearchAgentState, config):
    logger.info(">>> [Node] Entering Construct Node")
    if check_cancelled(config): return {}
    cb = get_cb(config)
    
    flat_items = state.get("raw_search_items", [])
    validated_meta = state.get("validated_meta", {})
    enable_validation = state["search_config"].get("enable_validation", True)
    disciplines = state["disciplines"]
    
    chunks: List[Chunk] = []
    by_disc = {}
    
    if not flat_items:
        logger.warning("No flat items found, creating fallback chunk.")
        # Fallback Chunk
        chunks.append(Chunk(
            id=f"chunk-{uuid.uuid4().hex[:8]}",
            content="未检索到内容",
            discipline="System",
            source=SourceInfo(url="about:blank", title="No Results"),
            relevance_score=0.1, academic_value=0.1
        ))
    else:
        for disc, it in flat_items:
            meta = validated_meta.get(it.url, {})
            if enable_validation and meta.get("is_valid") is False:
                continue
            
            rel = float(meta.get("relevance_score", 0.65))
            chunks.append(Chunk(
                id=f"chunk-{uuid.uuid4().hex[:8]}",
                content=it.content,
                discipline=disc,
                source=SourceInfo(url=it.url, title=it.title),
                relevance_score=rel,
                academic_value=float(meta.get("academic_value", 0.55)),
                validation=ValidationInfo(is_validated=bool(enable_validation), confidence=rel, notes=meta.get("notes"))
            ))
            by_disc[disc] = by_disc.get(disc, 0) + 1

    logger.info(f"Constructed {len(chunks)} chunks.")
    cb("constructing", 90, {"by_discipline": by_disc, "total": len(chunks)})
    return {"chunks": chunks}

async def ingest_node(state: SearchAgentState, config):
    logger.info(">>> [Node] Entering Ingest Node")
    if check_cancelled(config): return {}
    cb = get_cb(config)
    cb("ingesting", 95, None)
    
    concept = state["concept"]
    chunks = state.get("chunks", [])
    auto_ingest = state["search_config"].get("auto_ingest", True)
    
    status = "skipped"
    if auto_ingest and chunks:
        try:
            logger.info(f"Ingesting {len(chunks)} chunks to Knowledge Engine...")
            await knowledge_service.ingest_and_build_graph(concept, chunks)
            status = "success"
        except Exception as e:
            logger.error(f"!!! Ingestion FAILED: {e}")
            import traceback
            traceback.print_exc()
            status = "failed"
            
    cb("completed", 100, {"ingest_status": status})
    return {"graph_status": status}

# --- Workflow ---
workflow = StateGraph(SearchAgentState)
workflow.add_node("search", search_node)
workflow.add_node("validate", validation_node)
workflow.add_node("construct", construct_chunks_node)
workflow.add_node("ingest", ingest_node)

workflow.set_entry_point("search")
workflow.add_edge("search", "validate")
workflow.add_edge("validate", "construct")
workflow.add_edge("construct", "ingest")
workflow.add_edge("ingest", END)

search_graph = workflow.compile()