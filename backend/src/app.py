import os
import tempfile
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, WebSocket, Query, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response, FileResponse
import asyncio
import sys

from src.utils.helpers import ensure_supported_ext, save_upload_to_temp, download_to_temp
from src.services.ppt_parser_service import DocumentParserService
from src.services.ppt_expansion_service import PPTExpansionService
from src.services.page_analysis_service import PageDeepAnalysisService
from src.services.ai_tutor_service import AITutorService, ChatMessage
from src.services.reference_search_service import ReferenceSearchService
from src.services.vector_store_service import VectorStoreService
from src.agents.base import LLMConfig
from pydantic import BaseModel, Field

from src.services.mindmap_service import MindmapService
from src.services.persistence_service import PersistenceService
from src.services.export_service import ExportService
from src.services.keyword_extraction_service import KeywordExtractionService

app = FastAPI(title="PPTAS Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ai_tutor_service = None
_page_analysis_service = None
_persistence_service = None

def get_ai_tutor():
    """获取 AI 助教服务单例"""
    global _ai_tutor_service
    if _ai_tutor_service is None:
        config = load_config()
        llm_config = LLMConfig(
            api_key=config["llm"]["api_key"],
            base_url=config["llm"]["base_url"],
            model=config["llm"]["model"]
        )
        _ai_tutor_service = AITutorService(llm_config)
    return _ai_tutor_service

def get_page_analysis():
    """获取页面分析服务单例"""
    global _page_analysis_service
    if _page_analysis_service is None:
        config = load_config()
        llm_config = LLMConfig(
            api_key=config["llm"]["api_key"],
            base_url=config["llm"]["base_url"],
            model=config["llm"]["model"]
        )
        _page_analysis_service = PageDeepAnalysisService(llm_config)
    return _page_analysis_service
# ==================== 请求/响应模型 ====================
class ChatRequest(BaseModel):
    """聊天请求"""
    page_id: int
    message: str


class ChatResponse(BaseModel):
    """聊天响应"""
    page_id: int
    response: str
    timestamp: str


class PageAnalysisRequest(BaseModel):
    """页面分析请求"""
    doc_id: Optional[str] = None  
    page_id: int
    title: str
    content: str
    raw_points: Optional[list] = None
    key_concepts: Optional[list] = None 
    analysis: Optional[str] = None  
    force: Optional[bool] = False 


class ReferenceSearchRequest(BaseModel):
    """参考文献搜索请求"""
    query: str
    max_results: int = 10
    search_type: Optional[str] = None  


class SemanticSearchRequest(BaseModel):
    """语义搜索请求"""
    query: str
    top_k: int = 5
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    min_score: float = 0.0


class ExportRequest(BaseModel):
    """导出请求"""
    doc_id: str
    include_global: bool = True 
    include_pages: bool = True  
    page_range: Optional[List[int]] = None  
    export_type: str = "full" 
    file_name: Optional[str] = None
    file_type: Optional[str] = None  
    min_score: float = 0.0


class KeywordExtractionRequest(BaseModel):
    """关键词提取请求"""
    page_id: int
    title: str = ""
    content: str
    raw_points: Optional[List[dict]] = None
    knowledge_clusters: Optional[List[dict]] = None
    num_keywords: int = Field(default=5, ge=1, le=10)


# ==================== 配置加载 ====================
def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
    
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # 默认配置
    return {
        "llm": {
            "api_key": os.getenv("api_key", ""),
            "base_url": os.getenv("base_url", "https://api.openai.com/v1"),
            "model": os.getenv("model", "gpt-4")
        },
        "retrieval": {
            "preferred_sources": ["arxiv", "wikipedia"],
            "max_results": 3,
            "local_rag_priority": True
        },
        "expansion": {
            "max_revisions": 2,
            "min_gap_priority": 3,
            "temperature": 0.7
        }
    }


def get_persistence_service() -> PersistenceService:
    """获取 SQLite 持久化服务单例"""
    global _persistence_service
    if _persistence_service is None:
        backend_root = os.path.join(os.path.dirname(__file__), "..")  
        db_path = os.path.abspath(os.path.join(backend_root, "pptas_cache.sqlite3"))
        _persistence_service = PersistenceService(db_path=db_path)
        print(f"🗄️  SQLite 持久化启用: {db_path}")
    return _persistence_service


_persistence_service = None


def get_persistence_service() -> PersistenceService:
    """获取 SQLite 持久化服务单例"""
    global _persistence_service
    if _persistence_service is None:
        backend_root = os.path.join(os.path.dirname(__file__), "..") 
        db_path = os.path.abspath(os.path.join(backend_root, "pptas_cache.sqlite3"))
        _persistence_service = PersistenceService(db_path=db_path)
        print(f"🗄️  SQLite 持久化启用: {db_path}")
    return _persistence_service


def get_parser_service():
    return DocumentParserService()

def get_mindmap_service():
    return MindmapService()


class MindmapRequest(BaseModel):
    title: str = Field(default="", description="Slide title")
    raw_points: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        default=None,
        description="Slide points; supports plain strings or objects like {text, level}.",
    )
    max_depth: int = Field(default=4, ge=1, le=8)
    max_children_per_node: int = Field(default=20, ge=1, le=100)


class SlidePoint(BaseModel):
    text: str
    level: int = Field(default=0, ge=0)


class SlideItem(BaseModel):
    title: str
    page_num: Optional[int] = None
    raw_points: Optional[List[Union[str, Dict[str, Any], SlidePoint]]] = None


class MindmapFromSlidesRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="整体 PPT 标题，可选")
    slides: List[SlideItem]
    max_depth: int = Field(default=4, ge=1, le=8)
    max_children_per_node: int = Field(default=20, ge=1, le=100)


class MindmapFromGlobalAnalysisRequest(BaseModel):
    doc_id: str = Field(description="文档ID，用于获取全局分析结果")
    title: Optional[str] = Field(default=None, description="整体 PPT 标题，可选（默认使用全局分析的主题）")
    max_depth: int = Field(default=4, ge=1, le=8)
    max_children_per_node: int = Field(default=20, ge=1, le=100)


@app.post("/api/v1/mindmap")
async def build_mindmap(
    payload: MindmapRequest,
    svc: MindmapService = Depends(get_mindmap_service),
):
    """
    Build a mindmap tree for the frontend "思维导图" tab.
    Returns: { root: {id,label,children:[...] } }
    """
    return svc.build_mindmap(
        title=payload.title,
        raw_points=payload.raw_points,
        max_depth=payload.max_depth,
        max_children_per_node=payload.max_children_per_node,
    )


@app.post("/api/v1/mindmap/from-slides")
async def build_mindmap_from_slides(
    payload: MindmapFromSlidesRequest,
    svc: MindmapService = Depends(get_mindmap_service),
):
    """
    Build a mindmap for the entire PPT (all slides).
    Expects slides from /api/v1/expand-ppt output.
    """
    return svc.build_mindmap_for_ppt(
        slides=[s.model_dump() for s in payload.slides],
        deck_title=payload.title or "PPT Mindmap",
        max_depth=payload.max_depth,
        max_children_per_node=payload.max_children_per_node,
    )


@app.post("/api/v1/mindmap/from-global-analysis")
async def build_mindmap_from_global_analysis(
    payload: MindmapFromGlobalAnalysisRequest,
    svc: MindmapService = Depends(get_mindmap_service),
    persistence: PersistenceService = Depends(get_persistence_service),
):
    """
    Build a mindmap from global analysis results.
    Uses the global_analysis_json stored in the database for the given doc_id.
    """
    # 获取文档和全局分析结果
    doc = persistence.get_document_by_id(payload.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"文档不存在: {payload.doc_id}")
    
    global_analysis = doc.get("global_analysis")
    if not global_analysis:
        raise HTTPException(
            status_code=400,
            detail=f"文档 {payload.doc_id} 尚未进行全局分析，请先执行全局分析"
        )
    
    # 使用全局分析结果生成思维导图
    return svc.build_mindmap_from_global_analysis(
        global_analysis=global_analysis,
        deck_title=payload.title,
        max_depth=payload.max_depth,
        max_children_per_node=payload.max_children_per_node,
    )

def get_expansion_service():
    config = load_config()
    llm_config = LLMConfig(
        api_key=config["llm"]["api_key"],
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"]
    )
    return PPTExpansionService(llm_config)


def get_page_analysis_service():
    config = load_config()
    llm_config = LLMConfig(
        api_key=config["llm"]["api_key"],
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"]
    )
    return PageDeepAnalysisService(llm_config)


def get_ai_tutor_service():
    config = load_config()
    llm_config = LLMConfig(
        api_key=config["llm"]["api_key"],
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"]
    )
    return AITutorService(llm_config)


def get_keyword_extraction_service():
    config = load_config()
    llm_config = LLMConfig(
        api_key=config["llm"]["api_key"],
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"]
    )
    return KeywordExtractionService(llm_config)


def get_reference_search_service():
    return ReferenceSearchService()


def get_vector_store_service():
    """获取向量存储服务实例"""
    config = load_config()
    llm_config = LLMConfig(
        api_key=config["llm"]["api_key"],
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"]
    )
    # 优先使用 vector_store 配置，如果没有则使用 knowledge_base 路径
    vector_db_path = config.get("vector_store", {}).get("path") or config.get("knowledge_base", {}).get("path", "./ppt_vector_db")
    # 从配置读取embedding模型，如果没有则使用None
    embedding_model = config.get("vector_store", {}).get("embedding_model")
    return VectorStoreService(llm_config, vector_db_path, embedding_model=embedding_model)


# ==================== API 端点 ====================

@app.post("/api/v1/expand-ppt")
async def expand_ppt(
    file: Optional[UploadFile] = File(None),
    url_query: Optional[str] = Query(None, alias="url"),
    url_body: Optional[str] = Body(None),
    url_form: Optional[str] = Form(None, alias="url"),
    parser: DocumentParserService = Depends(get_parser_service),
    vector_store: VectorStoreService = Depends(get_vector_store_service),
    persistence: PersistenceService = Depends(get_persistence_service),
):
    """接收 PPTX/PDF 文件或 URL，返回解析后的逻辑结构，并存储到向量数据库。"""
    incoming_url = (url_form or url_body or url_query or "").strip() if url_form or url_body or url_query else None

    if not file and not incoming_url:
        raise HTTPException(status_code=400, detail="需要上传文件或提供 url")

    tmp_path = None
    try:
        if incoming_url:
            tmp_path, filename = download_to_temp(incoming_url)
        else:
            tmp_path, filename = await save_upload_to_temp(file)

        ext = ensure_supported_ext(filename)

        file_hash = persistence.sha256_file(tmp_path)
        existing_doc = persistence.get_document_by_hash(file_hash)
        if existing_doc:
            print(f"♻️  命中文档缓存: {filename} hash={file_hash[:12]} doc_id={existing_doc['doc_id']}")
            
            try:
                slides = existing_doc.get("slides", [])
                file_type = ext[1:] if ext.startswith('.') else ext
                
                # 检查向量数据库中是否已存储
                existing_vectors = vector_store.search_by_file(filename)
                if not existing_vectors or len(existing_vectors) == 0:
                    print(f"🔄 向量数据库中未找到此文件，开始存储...")
                    store_result = vector_store.store_document_slides(
                        file_name=filename,
                        file_type=file_type,
                        slides=slides
                    )
                    print(f"✅ 已存储 {store_result.get('total_chunks', 0)} 个切片到向量数据库")
                else:
                    print(f"✅ 向量数据库中已存在此文件（{len(existing_vectors)} 个切片）")
            except Exception as e:
                print(f"⚠️  向量数据库检查/存储失败: {e}")
            
            return {
                "doc_id": existing_doc["doc_id"],
                "file_hash": file_hash,
                "slides": existing_doc.get("slides", []),
                "cached": True,
            }

        slides = parser.parse_document(tmp_path, ext)
        
        # 存储到向量数据库
        print(f"\n🔄 准备存储到向量数据库: {filename}")
        try:
            file_type = ext[1:] if ext.startswith('.') else ext  
            store_result = vector_store.store_document_slides(
                file_name=filename,
                file_type=file_type,
                slides=slides
            )
            print(f"✅ 已存储 {store_result.get('total_chunks', 0)} 个切片到向量数据库")
        except Exception as e:
            print(f"❌ 存储到向量数据库失败: {e}")
            import traceback
            traceback.print_exc()

        # 每次上传后都保存解析结果（供下次同 PPT 复用）
        doc_id = str(uuid.uuid4())
        file_type = ext[1:] if ext.startswith('.') else ext
        persistence.upsert_document(
            doc_id=doc_id,
            file_name=filename,
            file_type=file_type,
            file_hash=file_hash,
            slides=slides,
        )
        
        return {
            "doc_id": doc_id,
            "file_hash": file_hash,
            "slides": slides,
            "vector_store": {
                "stored": True,
                "total_chunks": store_result.get("total_chunks", 0) if 'store_result' in locals() else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/v1/analyze-page")
async def analyze_page(
    request: PageAnalysisRequest,
    service: PageDeepAnalysisService = Depends(get_page_analysis_service),
    persistence: PersistenceService = Depends(get_persistence_service),
):
    """对单个页面进行深度分析 - 优化的 Agent 流程
    
    Args:
        request: 分析请求
        service: 分析服务
    
    Returns:
        页面深度分析结果（结构化分析、知识缺口、补充说明等）
    """
    try:
        # 如果 force=True，则忽略缓存，强制重新分析
        if request.doc_id and not request.force:
            cached = persistence.get_page_analysis(request.doc_id, request.page_id)
            if cached:
                return {"success": True, "cached": True, "data": cached}

        result = service.analyze_page(
            page_id=request.page_id,
            title=request.title,
            content=request.content,
            raw_points=request.raw_points
        )
        payload = {
            "success": True,
            "data": {
                "page_id": result.page_id,
                "title": result.title,
                "raw_content": result.raw_content,
                "page_structure": result.page_structure,
                "knowledge_clusters": result.knowledge_clusters,
                "understanding_notes": result.understanding_notes,
                "knowledge_gaps": result.knowledge_gaps,
                "expanded_content": result.expanded_content,
                "references": result.references,
                "raw_points": result.raw_points
            }
        }

        if request.doc_id:
            persistence.upsert_page_analysis(request.doc_id, request.page_id, payload["data"])
        return payload
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ 页面分析错误: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "details": error_trace}
        )


@app.get("/api/v1/page-analysis")
async def get_page_analysis_api(
    doc_id: str = Query(..., description="上传返回的文档ID"),
    page_id: int = Query(..., description="页面编号，从1开始"),
    persistence: PersistenceService = Depends(get_persistence_service),
):
    """获取单页历史分析（若存在）。"""
    cached = persistence.get_page_analysis(doc_id, page_id)
    return {"success": True, "data": cached}


@app.get("/api/v1/page-analysis/all")
async def get_all_page_analysis(
    doc_id: str = Query(..., description="上传返回的文档ID"),
    persistence: PersistenceService = Depends(get_persistence_service),
):
    """获取文档所有已保存的页分析（字典，key 为 page_id）。"""
    data = persistence.list_page_analyses(doc_id)
    return {"success": True, "data": data}


class GlobalAnalysisRequest(BaseModel):
    """全局分析请求"""
    doc_id: str
    force: Optional[bool] = False  


@app.post("/api/v1/analyze-document-global")
async def analyze_document_global(
    request: GlobalAnalysisRequest,
    service: PageDeepAnalysisService = Depends(get_page_analysis_service),
    persistence: PersistenceService = Depends(get_persistence_service),
):
    """对整个文档进行全局分析，获取主题和知识点框架
    
    这个接口应该在文档上传后调用，用于：
    1. 分析整个文档的主题和结构
    2. 提取全局知识点框架
    3. 识别知识逻辑流程
    
    Args:
        request: 全局分析请求，包含 doc_id 和可选的 force 参数
    """
    try:
        doc = persistence.get_document_by_id(request.doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="未找到文档")
        
        # 检查是否已有全局分析
        if not request.force and doc.get("global_analysis"):
            print(f"♻️  文档 {request.doc_id} 已有全局分析，直接返回")
            return {
                "success": True,
                "doc_id": request.doc_id,
                "global_analysis": doc["global_analysis"],
                "cached": True
            }
        
        if request.force:
            print(f"🔄 强制重新进行全局分析，忽略缓存 (doc_id={request.doc_id})")
        
        slides = doc.get("slides", [])
        if not slides:
            raise HTTPException(status_code=400, detail="文档没有slides数据")
        
        # 提取所有页面的文本内容
        ppt_texts = []
        for slide in slides:
            # 提取文本内容
            content_parts = []
            if slide.get("title"):
                content_parts.append(f"标题: {slide['title']}")
            if slide.get("raw_points"):
                for point in slide["raw_points"]:
                    if isinstance(point, dict):
                        content_parts.append(point.get("text", ""))
                    elif isinstance(point, str):
                        content_parts.append(point)
            if slide.get("raw_content"):
                content_parts.append(slide["raw_content"])
            
            slide_text = "\n".join(content_parts)
            if slide_text.strip():
                ppt_texts.append(slide_text)
        
        print(f"📊 开始全局分析，文档 {request.doc_id}，共 {len(ppt_texts)} 页")
        
        # 使用 GlobalStructureAgent 进行全局分析
        from src.agents.models import CheckResult
        state = {
            "ppt_texts": ppt_texts,
            "global_outline": {},
            "knowledge_units": [],
            "current_unit_id": "global",
            "current_page_id": 0,
            "raw_text": "\n\n".join([f"第{i+1}页:\n{text}" for i, text in enumerate(ppt_texts)]),
            "page_structure": {},
            "knowledge_clusters": [],
            "understanding_notes": "",
            "knowledge_gaps": [],
            "expanded_content": [],
            "retrieved_docs": [],
            "check_result": CheckResult(status="pass", issues=[], suggestions=[]),
            "final_notes": "",
            "revision_count": 0,
            "max_revisions": 1,
            "streaming_chunks": []
        }
        
        # 步骤1: 全局结构解析
        print("⏳ 开始全局结构解析...")
        state = service.structure_agent.run(state)
        global_outline = state.get("global_outline", {})
        print(f"✅ 全局结构解析完成: {global_outline.get('main_topic', '未知主题')}")
        
        # 步骤2: 全局知识点聚类
        print("⏳ 开始全局知识点聚类...")
        from src.agents.base import KnowledgeClusteringAgent
        clustering_agent = KnowledgeClusteringAgent(service.llm_config)
        state = clustering_agent.run(state)
        knowledge_units = state.get("knowledge_units", [])
        print(f"✅ 全局知识点聚类完成: {len(knowledge_units)} 个知识点单元")
        
        # 构建全局分析结果
        global_analysis = {
            "main_topic": global_outline.get("main_topic", ""),
            "chapters": global_outline.get("chapters", []),
            "knowledge_flow": global_outline.get("knowledge_flow", ""),
            "knowledge_units": [
                {
                    "unit_id": unit.unit_id,
                    "title": unit.title,
                    "pages": unit.pages,
                    "core_concepts": unit.core_concepts
                } for unit in knowledge_units
            ],
            "total_pages": len(ppt_texts)
        }
        
        # 保存全局分析结果
        persistence.update_global_analysis(request.doc_id, global_analysis)
        print(f"✅ 全局分析完成并已保存: {request.doc_id}")
        
        return {
            "success": True,
            "doc_id": request.doc_id,
            "global_analysis": global_analysis,
            "cached": False
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"全局分析失败: {str(e)}")

@app.post("/api/v1/analyze-page-stream")
async def analyze_page_stream(
    request: PageAnalysisRequest,
    service: PageDeepAnalysisService = Depends(get_page_analysis_service),
    persistence: PersistenceService = Depends(get_persistence_service),
):
    """对单个页面进行流式深度分析 - 实时返回各 Agent 的结果
    
    Args:
        request: 分析请求
        service: 分析服务
    
    Returns:
        Server-Sent Events 流式响应
    """
    async def event_generator():
        try:
            # 如果 force=False 且有缓存，则直接回放缓存
            print(f"🔍 流式分析请求: doc_id={request.doc_id}, page_id={request.page_id}, force={request.force}")
            if request.doc_id and not request.force:
                cached = persistence.get_page_analysis(request.doc_id, request.page_id)
                if cached:
                    print(f"✅ 找到缓存分析结果，直接返回 (doc_id={request.doc_id}, page_id={request.page_id})")
                    yield f"data: {json.dumps({'stage': 'clustering', 'data': cached.get('knowledge_clusters', []), 'message': '已加载历史分析：知识聚类', 'cached': True})}\n\n"
                    await asyncio.sleep(0.01)  # 确保数据被发送
                    yield f"data: {json.dumps({'stage': 'understanding', 'data': cached.get('understanding_notes', ''), 'message': '已加载历史分析：学习笔记', 'cached': True})}\n\n"
                    await asyncio.sleep(0.01)
                    yield f"data: {json.dumps({'stage': 'gaps', 'data': cached.get('knowledge_gaps', []), 'message': '已加载历史分析：知识缺口', 'cached': True})}\n\n"
                    await asyncio.sleep(0.01)
                    yield f"data: {json.dumps({'stage': 'expansion', 'data': cached.get('expanded_content', []), 'message': '已加载历史分析：补充说明', 'cached': True})}\n\n"
                    await asyncio.sleep(0.01)
                    yield f"data: {json.dumps({'stage': 'retrieval', 'data': cached.get('references', []), 'message': '已加载历史分析：参考资料', 'cached': True})}\n\n"
                    await asyncio.sleep(0.01)
                    yield f"data: {json.dumps({'stage': 'complete', 'data': cached, 'message': '历史分析加载完成', 'cached': True})}\n\n"
                    await asyncio.sleep(0.01)
                    return
                else:
                    print(f"⚠️ 未找到缓存分析结果 (doc_id={request.doc_id}, page_id={request.page_id})")
            elif not request.doc_id:
                print(f"⚠️ doc_id 为空，无法检查缓存 (page_id={request.page_id})")
            elif request.force:
                print(f"🔄 强制重新分析，忽略缓存 (doc_id={request.doc_id}, page_id={request.page_id})")
            
            # 如果是强制重新分析，输出提示
            if request.force:
                yield f"data: {json.dumps({'stage': 'info', 'data': {}, 'message': '🔄 强制重新分析，忽略缓存...'})}\n\n"
                await asyncio.sleep(0.01)

            # 获取全局分析结果
            global_analysis = None
            if request.doc_id:
                doc = persistence.get_document_by_id(request.doc_id)
                if doc and doc.get("global_analysis"):
                    global_analysis = doc["global_analysis"]
                    print(f"📚 加载全局分析结果: 主题={global_analysis.get('main_topic', '未知')}, 知识点单元={len(global_analysis.get('knowledge_units', []))}")
                else:
                    print(f"⚠️  文档 {request.doc_id} 没有全局分析结果，将仅基于当前页面分析")
            
            # 步骤1: 知识聚类
            print("⏳ 开始知识聚类...")
            yield f"data: {json.dumps({'stage': 'clustering', 'data': [], 'message': '正在分析难点概念...'})}\n\n"
            await asyncio.sleep(0.01)
            
            knowledge_clusters = service.clustering_agent.run(
                request.content,
                global_context=global_analysis
            )
            print(f"✅ 知识聚类完成: {len(knowledge_clusters)} 个概念")
            clustering_msg = f'识别了 {len(knowledge_clusters)} 个难点概念'
            yield f"data: {json.dumps({'stage': 'clustering', 'data': knowledge_clusters, 'message': clustering_msg})}\n\n"
            await asyncio.sleep(0.01)
            
            # 步骤2: 学习笔记
            print("⏳ 开始生成学习笔记...")
            yield f"data: {json.dumps({'stage': 'understanding', 'data': '', 'message': '正在生成学习笔记...'})}\n\n"
            await asyncio.sleep(0.01)
            
            from src.agents.models import CheckResult
            
            # 构建全局上下文数据
            global_outline = {}
            knowledge_units = []
            if global_analysis:
                global_outline = {
                    "main_topic": global_analysis.get("main_topic", ""),
                    "chapters": global_analysis.get("chapters", []),
                    "knowledge_flow": global_analysis.get("knowledge_flow", "")
                }
                # 转换knowledge_units格式
                for unit in global_analysis.get("knowledge_units", []):
                    from src.agents.models import KnowledgeUnit
                    knowledge_units.append(KnowledgeUnit(
                        unit_id=unit.get("unit_id", ""),
                        title=unit.get("title", ""),
                        pages=unit.get("pages", []),
                        core_concepts=unit.get("core_concepts", []),
                        raw_texts=[]
                    ))
            
            state = {
                "ppt_texts": [request.content],
                "global_outline": global_outline,
                "knowledge_units": knowledge_units,
                "current_unit_id": f"page_{request.page_id}",
                "current_page_id": request.page_id,
                "raw_text": request.content,
                "page_structure": {},
                "knowledge_clusters": knowledge_clusters,
                "understanding_notes": "",
                "knowledge_gaps": [],
                "expanded_content": [],
                "retrieved_docs": [],
                "check_result": CheckResult(status="pass", issues=[], suggestions=[]),
                "final_notes": "",
                "revision_count": 0,
                "max_revisions": 1,
                "streaming_chunks": []
            }
            
            state = service.understanding_agent.run(state)
            understanding_notes = state.get("understanding_notes", "")
            print(f"✅ 学习笔记完成")
            yield f"data: {json.dumps({'stage': 'understanding', 'data': understanding_notes, 'message': '学习笔记已生成'})}\n\n"
            await asyncio.sleep(0.01)
            
            # 步骤3: 知识缺口
            print("⏳ 开始识别知识缺口...")
            yield f"data: {json.dumps({'stage': 'gaps', 'data': [], 'message': '正在识别知识缺口...'})}\n\n"
            await asyncio.sleep(0.01)
            
            state = service.gap_agent.run(state)
            gaps_data = [
                {
                    "concept": gap.concept,
                    "gap_types": gap.gap_types,
                    "priority": gap.priority
                } for gap in state.get("knowledge_gaps", [])
            ]
            print(f"✅ 缺口识别完成: {len(gaps_data)} 个缺口")
            gaps_msg = f'识别了 {len(gaps_data)} 个理解缺口'
            yield f"data: {json.dumps({'stage': 'gaps', 'data': gaps_data, 'message': gaps_msg})}\n\n"
            await asyncio.sleep(0.01)
            
            # 步骤4: 知识扩展
            print("⏳ 开始生成补充说明...")
            yield f"data: {json.dumps({'stage': 'expansion', 'data': [], 'message': '正在生成补充说明...'})}\n\n"
            await asyncio.sleep(0.01)
            
            state = service.expansion_agent.run(state)
            expanded_data = []
            if state.get("expanded_content"):
                for ec in state["expanded_content"]:
                    if hasattr(ec, 'concept'):
                        expanded_data.append({
                            "concept": ec.concept,
                            "gap_type": ec.gap_type,
                            "content": ec.content,
                            "sources": ec.sources
                        })
                    else:
                        expanded_data.append(ec)
            print(f"✅ 补充说明完成: {len(expanded_data)} 条")
            expansion_msg = f'生成了 {len(expanded_data)} 条补充说明'
            yield f"data: {json.dumps({'stage': 'expansion', 'data': expanded_data, 'message': expansion_msg})}\n\n"
            await asyncio.sleep(0.01)
            
            # 步骤5: 外部检索
            print("⏳ 开始搜索参考资料...")
            yield f"data: {json.dumps({'stage': 'retrieval', 'data': [], 'message': '正在搜索参考资料...'})}\n\n"
            await asyncio.sleep(0.01)
            
            state = service.retrieval_agent.run(state)
            retrieved_count = len(state.get('retrieved_docs', []))
            print(f"✅ 检索完成: {retrieved_count} 条参考")
            retrieval_msg = f'找到了 {retrieved_count} 条参考资料'
            yield f"data: {json.dumps({'stage': 'retrieval', 'data': [], 'message': retrieval_msg})}\n\n"
            await asyncio.sleep(0.01)
            
            # 步骤6-7: 校验和整理（参考文献已在RetrievalAgent中搜索完成）
            print("⏳ 进行一致性校验和内容整理...")
            state = service.consistency_agent.run(state)
            state = service.organization_agent.run(state)
            
            # 从retrieved_docs中提取参考文献
            references = []
            for doc in state.get('retrieved_docs', [])[:5]:
                references.append({
                    "title": doc.metadata.get("title", ""),
                    "url": doc.metadata.get("url", ""),
                    "source": doc.metadata.get("source", "Unknown"),
                    "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                })
            
            print("✅ 分析完全完成")
            complete_data = {
                "page_id": request.page_id,
                "title": request.title,
                "raw_content": request.content,
                "page_structure": state.get('page_structure', {}),
                "knowledge_clusters": knowledge_clusters,
                "understanding_notes": state.get("understanding_notes", ""),
                "knowledge_gaps": gaps_data,
                "expanded_content": expanded_data,
                "references": references,
                "raw_points": request.raw_points or [],
            }

            if request.doc_id:
                persistence.upsert_page_analysis(request.doc_id, request.page_id, complete_data)

            yield f"data: {json.dumps({'stage': 'complete', 'data': complete_data, 'message': '分析完成！'})}\n\n"
            await asyncio.sleep(0.01)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ 流式分析错误: {error_trace}")
            error_msg = f'错误: {str(e)}'
            yield f"data: {json.dumps({'stage': 'error', 'data': {}, 'message': error_msg})}\n\n"
    
    headers = {
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


@app.post("/api/v1/chat")
async def chat(
    request: ChatRequest,
):
    """与 AI 助教对话"""
    try:
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="消息不能为空")
        
        # 获取服务实例
        service = get_ai_tutor()
        
        print(f"📝 聊天请求: page_id={request.page_id}, 已有上下文: {list(service.page_context.keys())}")
        
        # 检查是否已设置上下文
        if request.page_id not in service.page_context:
            print(f"⚠️ 页面 {request.page_id} 未在上下文中，当前已知页面: {list(service.page_context.keys())}")
            return {
                "status": "error",
                "response": f"⚠️ 页面内容未加载。请确保：\n1. 已切换到聊天标签页\n2. 已加载 PPT 内容\n3. 页面已完全初始化（page_id={request.page_id}）\n\n如果问题持续存在，请：\n• 刷新页面\n• 重新上传 PPT\n• 查看后端日志",
                "need_context": True
            }
        
        # 调用助教服务
        response_text = service.chat(request.page_id, request.message)
        
        return {
            "status": "ok",
            "response": response_text,
            "page_id": request.page_id,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ 聊天失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "response": f"❌ 抱歉,AI 暂时无法回答。错误: {str(e)}",
            "error": str(e)
        }

@app.post("/api/v1/tutor/set-context")
async def set_tutor_context(
    request: PageAnalysisRequest,
):
    """设置 AI 助教的页面上下文 - 与优化的知识分析结构对齐"""
    try:
        # 获取服务实例
        service = get_ai_tutor()
        
        # 组装内容文本
        content_text = request.content
        if not content_text and request.raw_points:
            content_text = "\n".join([
                point.get('text', '') 
                for point in request.raw_points 
                if point.get('type') == 'text'
            ])
        
        # 确保 page_id 是整数
        page_id = int(request.page_id)
        
        # 检查上下文是否已存在
        if page_id in service.page_context:
            print(f"✅ 上下文已存在（批量设置已完成），跳过重复设置: page_id={page_id}")
            greeting = service.get_assistant_greeting(page_id)
            return {
                "status": "ok",
                "page_id": page_id,
                "greeting": greeting,
                "message": "页面上下文已存在（批量设置）",
                "cached": True
            }
        
        print(f"🔧 设置上下文: page_id={page_id}, title={request.title}")
        
        # 提取知识集群信息
        knowledge_clusters = request.key_concepts or []
        if isinstance(knowledge_clusters, list) and len(knowledge_clusters) > 0:
            if isinstance(knowledge_clusters[0], str):
                knowledge_clusters = [
                    {"concept": c, "difficulty_level": 2} 
                    for c in knowledge_clusters
                ]
        
        # 设置页面上下文 
        service.set_page_context(
            page_id=page_id,
            title=request.title,
            content=content_text,
            knowledge_clusters=knowledge_clusters or [],
            understanding_notes=request.analysis or "",  
            knowledge_gaps=getattr(request, 'knowledge_gaps', []),
            expanded_content=getattr(request, 'expanded_content', [])
        )
        
        print(f"✅ 上下文已保存，当前已知页面: {list(service.page_context.keys())}")
        
        # 返回欢迎语
        greeting = service.get_assistant_greeting(page_id)
        
        return {
            "status": "ok",
            "page_id": page_id,
            "greeting": greeting,
            "message": "页面上下文已设置",
            "cached": False
        }
    
    except Exception as e:
        print(f"❌ 设置上下文失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class BulkContextRequest(BaseModel):
    """批量上下文请求"""
    doc_id: str

@app.post("/api/v1/tutor/set-context-bulk")
async def set_tutor_context_bulk(
    request: BulkContextRequest,
    persistence: PersistenceService = Depends(get_persistence_service),
):
    """为文档的所有页面批量设置上下文（优先使用已保存的分析结果）。"""
    try:
        doc_id = request.doc_id
        print(f"🚀 开始批量设置上下文，doc_id={doc_id}")
        service = get_ai_tutor()
        doc = persistence.get_document_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="未找到文档")

        analyses = persistence.list_page_analyses(doc_id)
        slides = doc.get("slides", [])
        set_pages = []
        
        print(f"📄 文档共有 {len(slides)} 页，已保存分析 {len(analyses)} 页")

        for idx, slide in enumerate(slides):
            page_id = slide.get("page_num") or (idx + 1)
            analysis = analyses.get(page_id, {})

            raw_points = slide.get("raw_points") or []
            content_text = analysis.get("raw_content") or slide.get("raw_content") or ""
            if not content_text and raw_points:
                content_text = "\n".join(
                    [p.get("text", "") if isinstance(p, dict) else str(p) for p in raw_points]
                )

            title = analysis.get("title") or slide.get("title") or f"Page {page_id}"
            print(f"  📄 设置页面 {page_id}: {title[:30]}... (有分析: {page_id in analyses})")
            
            service.set_page_context(
                page_id=page_id,
                title=title,
                content=content_text,
                knowledge_clusters=analysis.get("knowledge_clusters", []),
                understanding_notes=analysis.get("understanding_notes", ""),
                knowledge_gaps=analysis.get("knowledge_gaps", []),
                expanded_content=analysis.get("expanded_content", []),
            )
            set_pages.append(page_id)

        print(f"✅ 批量上下文设置完成，共 {len(set_pages)} 页: {set_pages}")
        return {
            "status": "ok",
            "doc_id": doc_id,
            "pages": set_pages,
            "message": f"批量上下文已设置，共 {len(set_pages)} 页"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tutor/debug/{page_id}")
async def debug_tutor_context(page_id: int):
    """调试：查看当前页面上下文"""
    service = get_ai_tutor()
    context = service.page_context.get(page_id)
    conversation = service.get_conversation_history(page_id)
    
    return {
        "page_id": page_id,
        "has_context": context is not None,
        "context": context,
        "conversation_count": len(conversation),
        "conversation": conversation[-5:] if conversation else []
    }

@app.post("/api/v1/tutor/conversation")
async def get_conversation_history(
    page_id: int,
    service: AITutorService = Depends(get_ai_tutor_service),
):
    """获取对话历史
    
    Args:
        page_id: 页面 ID
        service: AI 助教服务
    
    Returns:
        对话历史
    """
    try:
        history = service.get_conversation_history(page_id)
        return {
            "page_id": page_id,
            "messages": history
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/v1/search-references")
async def search_references(
    request: ReferenceSearchRequest,
    service: ReferenceSearchService = Depends(get_reference_search_service),
):
    """搜索参考文献（整合本地和外部搜索）
    
    Args:
        request: 搜索请求
        service: 搜索服务
    
    Returns:
        搜索结果
    """
    try:
        if request.search_type == "academic":
            result = await service.search_references_async(
                request.query, 
                request.max_results,
                preferred_sources=["arxiv"],
                use_external=True
            )
        elif request.search_type == "general":
            result = await service.search_references_async(
                request.query, 
                request.max_results,
                preferred_sources=["wikipedia", "web"],
                use_external=True
            )
        else:
            result = await service.search_references_async(
                request.query, 
                request.max_results,
                use_external=True
            )
        
        return {
            "success": True,
            "query": result.query,
            "total_results": result.total_results,
            "references": [
                {
                    "title": ref.title,
                    "url": ref.url,
                    "source": ref.source,
                    "snippet": ref.snippet,
                    "metadata": ref.metadata
                }
                for ref in result.references
            ]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/v1/search-by-concepts")
async def search_by_concepts(
    concepts: list,
    max_per_concept: int = 3,
    service: ReferenceSearchService = Depends(get_reference_search_service),
):
    """按概念搜索参考文献
    
    Args:
        concepts: 概念列表
        max_per_concept: 每个概念的最大结果数
        service: 搜索服务
    
    Returns:
        按概念组织的搜索结果
    """
    try:
        results = await service.search_by_concepts_async(concepts, max_per_concept, use_external=True)
        
        return {
            "success": True,
            "results": {
                concept: {
                    "query": result.query,
                    "total": result.total_results,
                    "references": [
                        {
                            "title": ref.title,
                            "url": ref.url,
                            "source": ref.source,
                            "snippet": ref.snippet,
                            "metadata": ref.metadata
                        }
                        for ref in result.references
                    ]
                }
                for concept, result in results.items()
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


class ExternalSearchRequest(BaseModel):
    """外部搜索请求"""
    query: str
    sources: Optional[List[str]] = None  
    max_results: int = 10


@app.post("/api/v1/search-external")
async def search_external(
    request: ExternalSearchRequest,
    service: ReferenceSearchService = Depends(get_reference_search_service),
):
    """外部资源搜索（Wikipedia、Arxiv、Web）
    
    Args:
        request: 外部搜索请求
        service: 搜索服务
    
    Returns:
        外部搜索结果
    """
    try:
        # 检查外部搜索是否可用
        if not service.external_search.is_available():
            return {
                "success": False,
                "error": "外部搜索服务不可用，请安装依赖: pip install wikipedia arxiv duckduckgo-search",
                "available_sources": []
            }
        
        # 执行外部搜索（直接使用 await，因为已经在异步上下文中）
        result = await service.external_search.search_all(
            request.query,
            sources=request.sources,
            max_results_per_source=max(2, request.max_results // 3)
        )
        
        return {
            "success": True,
            "query": result.query,
            "total_results": result.total_results,
            "sources_used": result.sources_used,
            "available_sources": service.external_search.get_available_sources(),
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "source": r.source,
                    "snippet": r.snippet,
                    "authors": r.authors,
                    "published": r.published
                }
                for r in result.results
            ]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "available_sources": service.external_search.get_available_sources() if hasattr(service, 'external_search') else []
            }
        )


@app.get("/api/v1/health")
async def health_check():
    """健康检查 - 轻量级，不调用任何服务依赖"""
    try:
        # 只返回静态信息，不涉及任何服务初始化
        return {
            "status": "ok",
            "version": "0.2.0",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # 即使出错也快速返回
        return {
            "status": "error",
            "message": str(e),
            "version": "0.2.0"
        }


@app.get("/api/v1/health/complete")
async def complete_health_check():
    """联合健康检查 - 同时检查后端和 LLM 连接（快速诊断）"""
    import asyncio
    import aiohttp
    
    config = load_config()
    llm_config = LLMConfig(
        api_key=config["llm"]["api_key"],
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"]
    )
    
    # 后端检查
    backend_status = {
        "status": "ok",
        "version": "0.2.0",
        "timestamp": datetime.now().isoformat()
    }
    
    # LLM 检查
    llm_status = {
        "status": "unknown",
        "message": "检查中...",
        "model": llm_config.model,
        "configured": bool(llm_config.api_key)
    }
    
    try:
        # 检查 API Key
        if not llm_config.api_key:
            llm_status["status"] = "error"
            llm_status["message"] = "API Key 未配置"
            llm_status["response_preview"] = "API Key 配置缺失"
        else:
            # 异步快速网络检查
            try:
                timeout = aiohttp.ClientTimeout(total=2, connect=1)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    base_url = llm_config.base_url or "https://api.openai.com/v1"
                    async with session.head(base_url, ssl=False, allow_redirects=True) as resp:
                        if resp.status in [200, 401, 403, 404]:
                            llm_status["status"] = "ok"
                            llm_status["message"] = "LLM 服务网络连接正常"
                            llm_status["response_preview"] = f"LLM 模型: {llm_config.model} ✓"
                        else:
                            llm_status["status"] = "warning"
                            llm_status["message"] = f"服务返回异常状态码 {resp.status}"
                            llm_status["response_preview"] = f"HTTP {resp.status}"
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
                llm_status["status"] = "error"
                llm_status["message"] = "无法连接到 LLM 服务"
                llm_status["response_preview"] = "连接超时"
    except Exception as e:
        llm_status["status"] = "error"
        llm_status["message"] = f"检查失败: {str(e)}"
        llm_status["response_preview"] = type(e).__name__
    
    return {
        "status": "ok",
        "backend": backend_status,
        "llm": llm_status,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/search-semantic")
async def search_semantic(
    request: SemanticSearchRequest,
    vector_store: VectorStoreService = Depends(get_vector_store_service),
):
    """基于语义搜索 PPT/PDF 切片
    
    Args:
        request: 搜索请求
        vector_store: 向量存储服务
    
    Returns:
        搜索结果列表
    """
    try:
        results = vector_store.search_similar_slides(
            query=request.query,
            top_k=request.top_k,
            file_name=request.file_name,
            file_type=request.file_type,
            min_score=request.min_score
        )
        
        return {
            "success": True,
            "query": request.query,
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        import traceback
        error_detail = str(e)
        traceback_str = traceback.format_exc()
        print(f"❌ 语义搜索失败: {error_detail}")
        print(f"详细错误:\n{traceback_str}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": error_detail,
                "message": "语义搜索失败，请检查后端日志"
            }
        )


@app.get("/api/v1/vector-store/stats")
async def get_vector_store_stats(
    vector_store: VectorStoreService = Depends(get_vector_store_service),
):
    """获取向量数据库统计信息
    
    Args:
        vector_store: 向量存储服务
    
    Returns:
        统计信息
    """
    try:
        stats = vector_store.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/v1/document/by-name/{file_name}")
async def get_document_by_name(
    file_name: str,
    persistence: PersistenceService = Depends(get_persistence_service),
):
    """通过文件名获取文档数据（用于跨文档跳转）
    
    Args:
        file_name: 文件名
        persistence: 持久化服务
    
    Returns:
        文档数据，包含 doc_id 和 slides
    """
    try:
        # 从数据库查询
        import sqlite3
        conn = sqlite3.connect(persistence.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT doc_id, file_name, file_type, slides_json FROM documents WHERE file_name = ?",
            (file_name,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            import json
            doc_id, file_name, file_type, slides_json = row
            slides = json.loads(slides_json) if slides_json else []
            
            return {
                "success": True,
                "doc_id": doc_id,
                "file_name": file_name,
                "file_type": file_type,
                "slides": slides
            }
        else:
            return JSONResponse(
                status_code=404,
                content={"error": f"文件 {file_name} 不存在"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/v1/vector-store/file/{file_name}")
async def get_file_slides(
    file_name: str,
    vector_store: VectorStoreService = Depends(get_vector_store_service),
):
    """获取特定文件的所有切片
    
    Args:
        file_name: 文件名
        vector_store: 向量存储服务
    
    Returns:
        该文件的所有切片
    """
    try:
        results = vector_store.search_by_file(file_name)
        return {
            "success": True,
            "file_name": file_name,
            "total_chunks": len(results),
            "chunks": results
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.delete("/api/v1/vector-store/file/{file_name}")
async def delete_file_slides(
    file_name: str,
    vector_store: VectorStoreService = Depends(get_vector_store_service),
):
    """删除特定文件的所有切片
    
    Args:
        file_name: 文件名
        vector_store: 向量存储服务
    
    Returns:
        删除结果
    """
    try:
        success = vector_store.delete_file_slides(file_name)
        return {
            "success": success,
            "file_name": file_name,
            "message": "删除成功" if success else "未找到文件或删除失败"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/v1/health/llm")
async def check_llm_connection():
    """检查 LLM 连接状态 - 轻量级快速诊断（不阻塞主线程）"""
    import asyncio
    import aiohttp
    from urllib.parse import urljoin
    
    config = load_config()
    llm_config = LLMConfig(
        api_key=config["llm"]["api_key"],
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"]
    )
    
    # 第一步：检查 API Key 配置
    if not llm_config.api_key:
        return {
            "status": "error",
            "message": "API Key 未配置",
            "detail": "请检查 config.json 中的 llm.api_key 字段",
            "configured": False,
            "model": llm_config.model,
            "response_preview": "API Key 配置缺失"
        }
    
    # 第二步：快速网络连接检查（不实际调用 LLM）
    try:
        timeout = aiohttp.ClientTimeout(total=2, connect=1)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            base_url = llm_config.base_url or "https://api.openai.com/v1"
            
            # 尝试连接到 base_url
            try:
                async with session.head(base_url, ssl=False, allow_redirects=True) as resp:
                    if resp.status in [200, 401, 403, 404]:
                        return {
                            "status": "ok",
                            "message": "LLM 服务网络连接正常（预检查）",
                            "model": llm_config.model,
                            "configured": True,
                            "base_url": base_url,
                            "response_preview": f"LLM 模型: {llm_config.model} ✓ 网络连接正常",
                            "note": "快速预检查只验证网络，实际 API 调用会在使用时进行"
                        }
                    else:
                        return {
                            "status": "warning",
                            "message": f"LLM 服务返回异常状态码 {resp.status}",
                            "model": llm_config.model,
                            "configured": True,
                            "base_url": base_url,
                            "response_preview": f"服务状态异常 (HTTP {resp.status})"
                        }
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
                # 网络连接失败
                return {
                    "status": "error",
                    "message": "无法连接到 LLM 服务",
                    "detail": f"连接超时或服务不可达：{base_url}",
                    "model": llm_config.model,
                    "configured": True,
                    "base_url": base_url,
                    "response_preview": f"连接失败: {base_url}"
                }
    except Exception as e:
        error_msg = str(e).lower()
        
        # 根据错误类型提供诊断
        if "401" in error_msg or "unauthorized" in error_msg:
            detail = "API Key 可能无效 - 请检查 config.json"
            preview = "认证失败: API Key 无效"
        elif "ssl" in error_msg or "certificate" in error_msg:
            detail = "SSL 证书问题 - 请检查网络或代理设置"
            preview = "SSL 证书错误"
        elif "connection" in error_msg or "refused" in error_msg:
            detail = "无法连接到 LLM 服务 - 检查 base_url 配置"
            preview = "无法连接到服务"
        else:
            detail = f"快速诊断失败：{str(e)}"
            preview = f"诊断错误: {type(e).__name__}"
        
        return {
            "status": "error",
            "message": "LLM 连接检查失败",
            "detail": detail,
            "model": llm_config.model,
            "configured": True,
            "response_preview": preview,
            "error_type": type(e).__name__
        }

class SetContextRequest(BaseModel):
    """设置页面上下文请求"""
    page_id: int
    title: str
    content: str
    raw_points: List[dict] = []
    key_concepts: List[str] = []
    analysis: str = ""


class ChatRequest(BaseModel):
    """聊天请求"""
    page_id: int
    message: str


# ===== API 端点 =====


@app.get("/api/v1/tutor/conversation")
async def get_conversation_history(page_id: int):
    """获取对话历史"""
    try:
        history = ai_tutor.get_conversation_history(page_id)
        return {
            "status": "ok",
            "page_id": page_id,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/tutor/conversation/{page_id}")
async def clear_conversation(page_id: int):
    """清除对话历史"""
    try:
        ai_tutor.clear_conversation(page_id)
        return {
            "status": "ok",
            "page_id": page_id,
            "message": "对话历史已清除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/export")
async def export_analysis(
    request: ExportRequest,
    persistence: PersistenceService = Depends(get_persistence_service)
):
    """
    导出AI分析补充内容为Markdown格式
    
    Args:
        request: 导出请求，包含doc_id、导出选项等
        
    Returns:
        Markdown格式的文件下载响应
    """
    try:
        # 1. 获取文档信息
        doc = persistence.get_document_by_id(request.doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"文档未找到: {request.doc_id}")
        
        doc_info = {
            "file_name": doc.get("file_name", "未知文档"),
            "file_type": doc.get("file_type", "unknown"),
            "created_at": doc.get("created_at", ""),
            "updated_at": doc.get("updated_at", "")
        }
        
        # 2. 获取全局分析
        global_analysis = doc.get("global_analysis") if request.include_global else None
        
        # 3. 获取页面分析
        page_analyses = None
        if request.include_pages:
            page_analyses = persistence.list_page_analyses(request.doc_id)
            
            # 如果指定了页面范围，只保留指定的页面
            if request.page_range:
                page_analyses = {
                    page_id: data 
                    for page_id, data in page_analyses.items() 
                    if page_id in request.page_range
                }
        
        # 4. 生成导出内容
        export_service = ExportService()
        
        if request.export_type == "summary":
            # 导出摘要
            total_pages = len(doc.get("slides", []))
            analyzed_pages = len(page_analyses) if page_analyses else 0
            
            markdown_content = export_service.export_summary_markdown(
                doc_info=doc_info,
                global_analysis=global_analysis,
                page_count=total_pages,
                analyzed_pages=analyzed_pages
            )
            file_name = f"{doc_info['file_name']}_AI分析摘要.md"
        else:
            # 导出完整内容
            markdown_content = export_service.export_to_markdown(
                doc_info=doc_info,
                global_analysis=global_analysis,
                page_analyses=page_analyses,
                include_global=request.include_global,
                include_pages=request.include_pages,
                page_range=request.page_range
            )
            file_name = f"{doc_info['file_name']}_AI分析补充内容.md"
        
        # 5. 返回文件下载响应
        from urllib.parse import quote
        encoded_filename = quote(file_name)
        
        return Response(
            content=markdown_content.encode('utf-8'),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename*=UTF-8\'\'{encoded_filename}',
                "Content-Type": "text/markdown; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ 导出失败: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"导出失败: {str(e)}"
        )


@app.post("/api/v1/extract-keywords")
async def extract_keywords(
    request: KeywordExtractionRequest,
    service: KeywordExtractionService = Depends(get_keyword_extraction_service),
):
    """提取页面关键词 - 5个有意义的中文名词短语
    
    Args:
        request: 关键词提取请求，包含页面ID、标题、内容等
        service: 关键词提取服务
    
    Returns:
        提取的关键词列表和统计信息
    """
    try:
        print(f"\n🔍 关键词提取请求: page_id={request.page_id}, title={request.title[:30]}")
        print(f"   content长度: {len(request.content) if request.content else 0}")
        print(f"   raw_points数量: {len(request.raw_points) if request.raw_points else 0}")
        
        keywords = service.extract_keywords(
            content=request.content,
            title=request.title,
            num_keywords=request.num_keywords,
            raw_points=request.raw_points
        )
        
        print(f"\n✅ 关键词提取完成: {keywords} (共{len(keywords)}个)")
        
        return {
            "success": True,
            "page_id": request.page_id,
            "keywords": keywords,
            "count": len(keywords),
            "message": f"成功提取 {len(keywords)} 个关键词"
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ 关键词提取失败: {str(e)}")
        print(f"详细错误:\n{error_trace}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "page_id": request.page_id,
                "error": str(e),
                "message": "关键词提取失败"
            }
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

