"""
PatPat-Inconsistency-Hunter API 路由定义
定义所有API端点和请求处理逻辑
"""

import asyncio
import json
import hashlib
from collections import Counter
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func, cast, String, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.schemas import (
    DocumentInput,
    AnalysisResult,
    AnalysisTask,
    TaskStatus,
    ConflictReport,
    FactWithSource,
)
from ..models.database import Document, FactRecord, ConflictRecord, AnalysisHistory, User, CollaborationRoom, RoomMembership, DocumentImage
from ..services.analysis_engine import AnalysisEngine, get_analysis_engine
from ..utils.redis_client import get_redis_client, RedisClient
from ..utils.db_session import get_db_session
from ..utils.logger import logger
from .auth_routes import get_current_user


router = APIRouter()


# ==================== 文档检测锁管理 ====================
# 存储正在检测的文档哈希，防止重复检测
_analyzing_documents = {}  # {content_hash: task_id}


async def acquire_analysis_lock(content_hash: str, task_id: str) -> bool:
    """
    获取文档分析锁
    返回 True 表示成功获取锁，False 表示文档正在被分析
    """
    # 检查内存锁
    if content_hash in _analyzing_documents:
        return False
    
    # 同时检查 Redis（分布式场景）
    try:
        redis_client = await get_redis_client()
        lock_key = f"analysis_lock:{content_hash}"
        
        # 尝试设置锁，如果已存在则失败
        result = await redis_client.client.set(lock_key, task_id, nx=True, ex=7200)  # 2小时过期
        if not result:
            return False
    except Exception as e:
        logger.warning(f"Redis锁获取失败，仅使用内存锁: {e}")
    
    # 设置内存锁
    _analyzing_documents[content_hash] = task_id
    return True


async def release_analysis_lock(content_hash: str):
    """释放文档分析锁"""
    # 释放内存锁
    if content_hash in _analyzing_documents:
        del _analyzing_documents[content_hash]
    
    # 释放 Redis 锁
    try:
        redis_client = await get_redis_client()
        lock_key = f"analysis_lock:{content_hash}"
        await redis_client.client.delete(lock_key)
    except Exception as e:
        logger.warning(f"Redis锁释放失败: {e}")


async def is_document_analyzing(content_hash: str) -> tuple[bool, str]:
    """
    检查文档是否正在被分析
    返回 (is_analyzing, task_id)
    """
    # 检查内存锁
    if content_hash in _analyzing_documents:
        return True, _analyzing_documents[content_hash]
    
    # 检查 Redis 锁
    try:
        redis_client = await get_redis_client()
        lock_key = f"analysis_lock:{content_hash}"
        task_id = await redis_client.client.get(lock_key)
        if task_id:
            return True, task_id.decode() if isinstance(task_id, bytes) else task_id
    except Exception as e:
        logger.warning(f"Redis锁查询失败: {e}")
    
    return False, ""


# ==================== 请求/响应模型 ====================

class AnalyzeRequest(BaseModel):
    """分析请求"""
    content: str = Field(..., description="文档内容（纯文本）", min_length=100)
    title: Optional[str] = Field(None, description="文档标题")
    content_json: Optional[Dict[str, Any]] = Field(None, description="富文本内容JSON（TipTap格式）")
    skip_verification: bool = Field(False, description="是否跳过事实验证")


class AnalyzeResponse(BaseModel):
    """分析响应"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: float
    current_step: str
    error_message: Optional[str] = None


class AnalysisResultResponse(BaseModel):
    """分析结果响应"""
    task_id: str
    document_title: Optional[str]
    document_length: int
    total_chunks: int
    total_facts: int
    total_conflicts: int
    verified_conflicts: int
    analysis_time: float
    conflict_type_distribution: dict
    severity_distribution: dict
    summary: dict


class FactListResponse(BaseModel):
    """事实列表响应"""
    task_id: str
    total: int
    facts: List[dict]


class ConflictListResponse(BaseModel):
    """冲突列表响应"""
    task_id: str
    total: int
    conflicts: List[dict]


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str


# ==================== 存储任务结果（内存缓存+数据库持久化） ====================
_task_results = {}
_task_documents = {}  # 存储文档原文


async def _get_document_by_task(task_id: str, db: AsyncSession) -> Optional[Document]:
    result = await db.execute(
        select(Document).where(Document.task_id == task_id)
    )
    return result.scalar_one_or_none()


def _format_location(chapter: Optional[str], section: Optional[str]) -> str:
    parts = []
    if chapter:
        parts.append(f"第{chapter}章")
    if section:
        parts.append(f"第{section}节")
    return " > ".join(parts) if parts else "文档开头"


async def save_analysis_to_db(
    task_id: str,
    content: str,
    title: Optional[str],
    result: AnalysisResult,
    user_id: Optional[str] = None,
    content_json: Optional[Dict[str, Any]] = None,
):
    """将分析结果保存到数据库（支持新增和更新）"""
    from ..utils.db_session import async_session_maker
    from ..services.document_editor import RichTextContent
    
    try:
        async with async_session_maker() as db:
            # 计算内容哈希
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # 处理富文本内容
            if content_json:
                content_html = RichTextContent.to_html(content_json)
            else:
                content_json = RichTextContent.from_plain_text(content)
                content_html = RichTextContent.to_html(content_json)
            
            # 检查是否已存在该 task_id 的文档（重新分析的情况）
            existing_doc_result = await db.execute(
                select(Document).where(Document.task_id == task_id)
            )
            existing_doc = existing_doc_result.scalar_one_or_none()
            
            if existing_doc:
                # 更新现有文档记录
                existing_doc.title = title or existing_doc.title
                existing_doc.content = content
                existing_doc.content_json = content_json
                existing_doc.content_html = content_html
                existing_doc.content_length = len(content)
                existing_doc.content_hash = content_hash
                existing_doc.status = "completed"
                existing_doc.progress = 100.0
                existing_doc.total_chunks = result.total_chunks
                existing_doc.total_facts = result.total_facts
                existing_doc.total_conflicts = result.total_conflicts
                existing_doc.analysis_time = result.analysis_time
                existing_doc.completed_at = datetime.now()
                existing_doc.updated_at = datetime.now()
                if user_id:
                    existing_doc.doc_metadata = {"user_id": user_id}
                doc = existing_doc
                await db.flush()
            else:
                # 创建新文档记录
                doc = Document(
                    task_id=task_id,
                    title=title,
                    content=content,
                    content_json=content_json,
                    content_html=content_html,
                    content_length=len(content),
                    content_hash=content_hash,
                    status="completed",
                    progress=100.0,
                    total_chunks=result.total_chunks,
                    total_facts=result.total_facts,
                    total_conflicts=result.total_conflicts,
                    analysis_time=result.analysis_time,
                    completed_at=datetime.now(),
                    doc_metadata={"user_id": user_id} if user_id else {},
                )
                db.add(doc)
                await db.flush()  # 获取document.id
            
            # 从 content_json 中提取图片并保存到 document_images 表
            import uuid
            if content_json:
                images_info = RichTextContent.extract_images(content_json)
                for img_info in images_info:
                    # 只保存有 imageId 或有效 src 的图片
                    image_id = img_info.get("imageId")
                    src = img_info.get("src", "")
                    
                    if image_id or (src and src.startswith("/api/uploads")):
                        # 检查是否已存在（避免重复）
                        existing = await db.execute(
                            select(DocumentImage).where(
                                (DocumentImage.image_id == image_id) if image_id
                                else (DocumentImage.file_url == src)
                            )
                        )
                        if existing.scalar_one_or_none() is None:
                            # 从 file_url 解析路径信息
                            import re
                            url_match = re.match(r"/api/uploads/images/(\d{4}/\d{2}/\d{2})/([^/]+)", src)
                            file_path = None
                            file_name = None
                            if url_match:
                                date_dir = url_match.group(1)
                                file_name = url_match.group(2)
                                from ..services.document_editor import UPLOAD_DIR
                                file_path = str(UPLOAD_DIR / date_dir / file_name)
                            
                            # 获取文件大小（如果文件存在）
                            file_size = 0
                            if file_path:
                                from pathlib import Path
                                path_obj = Path(file_path)
                                if path_obj.exists():
                                    file_size = path_obj.stat().st_size
                            
                            # 推断 MIME 类型
                            mime_type = "image/png"  # 默认值
                            if file_name:
                                ext = file_name.split('.')[-1].lower()
                                mime_map = {
                                    'png': 'image/png',
                                    'jpg': 'image/jpeg',
                                    'jpeg': 'image/jpeg',
                                    'gif': 'image/gif',
                                    'webp': 'image/webp',
                                    'svg': 'image/svg+xml',
                                }
                                mime_type = mime_map.get(ext, 'image/png')
                            
                            # 保存图片到 document_images 表，使用 task_id 关联 documents 表
                            doc_image = DocumentImage(
                                image_id=image_id or f"img_{uuid.uuid4().hex[:12]}",
                                task_id=task_id,  # 关联 documents.task_id
                                document_id=None,  # user_documents 的关联（如果有）
                                user_id=int(user_id) if user_id and user_id.isdigit() else None,
                                file_name=file_name or (src.split("/")[-1] if src else "image"),
                                file_path=file_path or src,
                                file_url=src,
                                file_size=file_size,
                                mime_type=mime_type,
                            )
                            db.add(doc_image)
            
            # 保存事实记录
            for fact in result.facts:
                # source_position 是 tuple[int, int]，需要分解
                source_start, source_end = fact.source_position if fact.source_position else (0, 0)
                
                # 检查是否来自图片
                fact_type_str = fact.fact_type.value if hasattr(fact.fact_type, 'value') else str(fact.fact_type)
                is_image_source = fact_type_str.startswith('image_') if fact_type_str else False
                
                fact_record = FactRecord(
                    fact_id=fact.fact_id,
                    document_id=doc.id,
                    content=fact.content,
                    fact_type=fact_type_str,
                    confidence=fact.confidence,
                    source_text=fact.source_text,
                    source_start=source_start,
                    source_end=source_end,
                    chapter=fact.chapter,
                    section=fact.section,
                    chunk_id=fact.source_chunk_id,  # 正确的属性名
                    is_image_source=is_image_source,
                    image_id=getattr(fact, 'image_source_id', None),
                    image_description=getattr(fact, 'image_description', None),
                )
                db.add(fact_record)
            
            # 保存冲突记录
            for conflict_report in result.conflicts:
                conflict = conflict_report.conflict
                verification = conflict_report.verification
                
                # 检查是否涉及图片冲突
                fact_a_type = conflict.fact_a.fact_type.value if hasattr(conflict.fact_a.fact_type, 'value') else str(conflict.fact_a.fact_type)
                fact_b_type = conflict.fact_b.fact_type.value if hasattr(conflict.fact_b.fact_type, 'value') else str(conflict.fact_b.fact_type)
                is_image_conflict = (
                    (fact_a_type and fact_a_type.startswith('image_')) or 
                    (fact_b_type and fact_b_type.startswith('image_'))
                )
                
                conflict_record = ConflictRecord(
                    conflict_id=conflict.conflict_id,
                    document_id=doc.id,
                    fact_a_id=conflict.fact_a.fact_id,
                    fact_b_id=conflict.fact_b.fact_id,
                    conflict_type=conflict.conflict_type.value,
                    severity=conflict.severity,
                    description=conflict.description,
                    suggestion=conflict.suggestion,
                    is_verified=verification is not None and verification.is_verified,
                    correct_fact=verification.correct_fact if verification else None,
                    verification_reasoning=verification.verification_reasoning if verification else None,
                    verification_confidence=verification.confidence if verification else None,
                    source_description=verification.source_description if verification else None,
                    verified_at=datetime.now() if verification and verification.is_verified else None,
                    is_image_conflict=is_image_conflict,
                )
                db.add(conflict_record)
            
            # 保存分析历史记录
            history = AnalysisHistory(
                task_id=task_id,
                step_name="analysis_complete",
                step_status="completed",
                step_detail=f"文档分析完成: {result.total_facts}个事实, {result.total_conflicts}个冲突",
                output_data={
                    "total_facts": result.total_facts,
                    "total_conflicts": result.total_conflicts,
                    "analysis_time": result.analysis_time,
                    "document_length": len(content),
                },
                duration=result.analysis_time,
            )
            db.add(history)
            
            await db.commit()
            logger.info(f"分析结果已保存到数据库: task_id={task_id}")
            
    except Exception as e:
        logger.error(f"保存分析结果到数据库失败: {e}")
        import traceback
        traceback.print_exc()


# ==================== API 端点 ====================

@router.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """
    健康检查
    
    返回服务运行状态
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
    )


@router.post("/analyze", response_model=AnalyzeResponse, tags=["分析"])
async def analyze_document(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    提交文档分析任务
    
    接收文档内容，启动后台分析任务，返回任务ID
    注意：同一文档在分析完成前不能重复提交
    """
    try:
        # 计算文档内容哈希，用于检测锁
        content_hash = hashlib.sha256(request.content.encode()).hexdigest()
        
        # 检查是否有相同文档正在分析
        is_analyzing, existing_task_id = await is_document_analyzing(content_hash)
        if is_analyzing:
            raise HTTPException(
                status_code=409,  # Conflict
                detail=f"该文档正在分析中，任务ID: {existing_task_id}。请等待分析完成后再试。"
            )
        
        # 使用增强版分析引擎（支持图片处理和LangGraph优化）
        from ..services.analysis_engine import get_enhanced_analysis_engine
        engine = get_enhanced_analysis_engine()
        document = DocumentInput(
            content=request.content,
            title=request.title,
        )
        
        # 创建任务
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        
        # 获取分析锁
        lock_acquired = await acquire_analysis_lock(content_hash, task_id)
        if not lock_acquired:
            raise HTTPException(
                status_code=409,
                detail="该文档正在分析中，请等待分析完成后再试。"
            )
        
        # 保存用户ID以便后续关联
        user_id = current_user.user_id if current_user else None
        
        # 在后台执行分析
        async def run_analysis():
            try:
                redis_client = await get_redis_client()
                
                async def progress_callback(tid: str, progress: float, step: str):
                    await redis_client.update_task_progress(tid, progress, step)
                
                result = await engine.analyze_document(
                    document=document,
                    task_id=task_id,
                    progress_callback=progress_callback,
                    skip_verification=request.skip_verification,
                    content_json=request.content_json,
                )
                
                # 保存结果到内存
                _task_results[task_id] = result
                
                # 保存文档原文到内存（用于结果页面展示）
                from ..services.document_editor import RichTextContent
                content_json = request.content_json
                content_html = RichTextContent.to_html(content_json) if content_json else ""
                _task_documents[task_id] = {
                    "content": request.content,
                    "title": request.title,
                    "content_json": content_json,
                    "content_html": content_html,
                }
                
                # 保存结果到数据库（包含富文本内容）
                await save_analysis_to_db(
                    task_id, 
                    request.content, 
                    request.title, 
                    result, 
                    user_id,
                    content_json=request.content_json
                )
                
                # 更新Redis中的任务状态
                await redis_client.save_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "current_step": "完成",
                })
                
            except Exception as e:
                logger.error(f"分析任务 {task_id} 失败: {e}")
                import traceback
                traceback.print_exc()
                try:
                    redis_client = await get_redis_client()
                    await redis_client.save_task(task_id, {
                        "status": "failed",
                        "progress": 0,
                        "current_step": "失败",
                        "error_message": str(e),
                    })
                except Exception:
                    pass
            finally:
                # 无论成功还是失败，都要释放锁
                await release_analysis_lock(content_hash)
        
        # 初始化任务状态
        try:
            redis_client = await get_redis_client()
            await redis_client.save_task(task_id, {
                "status": "pending",
                "progress": 0,
                "current_step": "等待处理",
            })
        except Exception as e:
            logger.warning(f"Redis不可用，任务状态将只保存在内存中: {e}")
        
        # 直接创建异步任务（不使用 BackgroundTasks，因为它在线程池中没有事件循环）
        asyncio.create_task(run_analysis())
        
        return AnalyzeResponse(
            task_id=task_id,
            status="pending",
            message="分析任务已提交，请使用task_id查询进度",
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"提交分析任务失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/task/{task_id}/status", response_model=TaskStatusResponse, tags=["任务"])
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    返回任务的当前状态和进度
    """
    try:
        redis_client = await get_redis_client()
        task_data = await redis_client.get_task(task_id)
        
        if not task_data:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return TaskStatusResponse(
            task_id=task_id,
            status=task_data.get("status", "unknown"),
            progress=task_data.get("progress", 0),
            current_step=task_data.get("current_step", ""),
            error_message=task_data.get("error_message"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/task/{task_id}/result", response_model=AnalysisResultResponse, tags=["任务"])
async def get_task_result(
    task_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取任务结果
    
    返回完整的分析结果摘要
    """
    result = _task_results.get(task_id)
    
    if not result:
        doc = await _get_document_by_task(task_id, db)
        if not doc:
            raise HTTPException(status_code=404, detail="结果不存在或任务未完成")
        
        conflict_rows = await db.execute(
            select(
                ConflictRecord.conflict_type,
                ConflictRecord.severity,
                ConflictRecord.is_verified,
            ).where(ConflictRecord.document_id == doc.id)
        )
        conflict_data = conflict_rows.all()
        type_counter = Counter(row[0] for row in conflict_data)
        severity_distribution = {
            "critical": sum(1 for _, severity, _ in conflict_data if severity >= 0.9),
            "high": sum(1 for _, severity, _ in conflict_data if 0.6 <= severity < 0.9),
            "medium": sum(1 for _, severity, _ in conflict_data if 0.3 <= severity < 0.6),
            "low": sum(1 for _, severity, _ in conflict_data if severity < 0.3),
        }
        verified_conflicts = sum(1 for _, _, verified in conflict_data if verified)
        
        summary = {
            "document_title": doc.title,
            "document_length": doc.content_length,
            "total_facts": doc.total_facts,
            "total_conflicts": doc.total_conflicts,
            "conflict_rate": round(doc.total_conflicts / max(doc.total_facts, 1) * 100, 2) if doc.total_facts else 0.0,
            "analysis_time": round(doc.analysis_time or 0.0, 2),
        }
        
        return AnalysisResultResponse(
            task_id=task_id,
            document_title=doc.title,
            document_length=doc.content_length,
            total_chunks=doc.total_chunks,
            total_facts=doc.total_facts,
            total_conflicts=doc.total_conflicts,
            verified_conflicts=verified_conflicts,
            analysis_time=doc.analysis_time or 0.0,
            conflict_type_distribution=dict(type_counter),
            severity_distribution=severity_distribution,
            summary=summary,
        )
    
    return AnalysisResultResponse(
        task_id=result.task_id,
        document_title=result.document_title,
        document_length=result.document_length,
        total_chunks=result.total_chunks,
        total_facts=result.total_facts,
        total_conflicts=result.total_conflicts,
        verified_conflicts=result.verified_conflicts,
        analysis_time=result.analysis_time,
        conflict_type_distribution=result.conflict_type_distribution,
        severity_distribution=result.severity_distribution,
        summary=result.get_summary(),
    )


@router.get("/task/{task_id}/facts", response_model=FactListResponse, tags=["任务"])
async def get_task_facts(
    task_id: str,
    page: int = 1,
    page_size: int = 20,
    fact_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取提取的事实列表
    
    支持分页和类型过滤
    """
    result = _task_results.get(task_id)
    
    if not result:
        doc = await _get_document_by_task(task_id, db)
        if not doc:
            raise HTTPException(status_code=404, detail="结果不存在或任务未完成")
        
        filters = [FactRecord.document_id == doc.id]
        if fact_type:
            filters.append(FactRecord.fact_type == fact_type)
        
        total = (await db.execute(
            select(func.count()).select_from(FactRecord).where(*filters)
        )).scalar_one()
        
        fact_query = (
            select(FactRecord)
            .where(*filters)
            .order_by(FactRecord.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        fact_records = (await db.execute(fact_query)).scalars().all()
        
        def record_to_dict(record: FactRecord) -> dict:
            return {
                "fact_id": record.fact_id,
                "content": record.content,
                "fact_type": record.fact_type,
                "confidence": record.confidence,
                "source_text": record.source_text,
                "source_position": (record.source_start, record.source_end),
                "source_chunk_id": record.chunk_id,
                "chapter": record.chapter,
                "section": record.section,
                "is_image_source": record.is_image_source or False,
                "image_id": record.image_id,
                "image_description": record.image_description,
            }
        
        return FactListResponse(
            task_id=task_id,
            total=total,
            facts=[record_to_dict(fr) for fr in fact_records],
        )
    
    facts = result.facts
    
    if fact_type:
        facts = [f for f in facts if f.fact_type == fact_type]
    
    total = len(facts)
    start = (page - 1) * page_size
    end = start + page_size
    facts = facts[start:end]
    
    # 确保从缓存返回的事实包含图片相关字段
    def ensure_fact_fields(fact):
        fact_dict = fact.model_dump() if hasattr(fact, 'model_dump') else dict(fact)
        
        # 确保 fact_type 是字符串
        fact_type = fact_dict.get('fact_type', '')
        if hasattr(fact_type, 'value'):
            fact_type = fact_type.value
        fact_dict['fact_type'] = str(fact_type) if fact_type else ""
        
        # 如果缺少字段，尝试从 fact_type 推断
        if 'is_image_source' not in fact_dict or fact_dict.get('is_image_source') is None:
            fact_dict['is_image_source'] = fact_dict['fact_type'].startswith('image_') if fact_dict['fact_type'] else False
        if 'image_id' not in fact_dict:
            fact_dict['image_id'] = getattr(fact, 'image_id', None)
        if 'image_description' not in fact_dict:
            fact_dict['image_description'] = getattr(fact, 'image_description', None)
        
        # 调试日志
        if fact_dict.get('is_image_source') or fact_dict['fact_type'].startswith('image_'):
            logger.info(f"📸 [get_task_facts] 图片事实: {fact_dict.get('fact_id')}, fact_type: {fact_dict['fact_type']}, image_id: {fact_dict.get('image_id')}")
        
        return fact_dict
    
    return FactListResponse(
        task_id=task_id,
        total=total,
        facts=[ensure_fact_fields(f) for f in facts],
    )


@router.get("/task/{task_id}/conflicts", response_model=ConflictListResponse, tags=["任务"])
async def get_task_conflicts(
    task_id: str,
    page: int = 1,
    page_size: int = 20,
    conflict_type: Optional[str] = None,
    min_severity: float = 0.0,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取检测到的冲突列表
    
    支持分页、类型过滤和严重程度过滤
    """
    result = _task_results.get(task_id)
    
    if not result:
        doc = await _get_document_by_task(task_id, db)
        if not doc:
            raise HTTPException(status_code=404, detail="结果不存在或任务未完成")
        
        filters = [ConflictRecord.document_id == doc.id]
        if conflict_type:
            filters.append(ConflictRecord.conflict_type == conflict_type)
        if min_severity > 0:
            filters.append(ConflictRecord.severity >= min_severity)
        
        total = (await db.execute(
            select(func.count()).select_from(ConflictRecord).where(*filters)
        )).scalar_one()
        
        conflict_query = (
            select(ConflictRecord)
            .where(*filters)
            .order_by(ConflictRecord.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        conflict_records = (await db.execute(conflict_query)).scalars().all()
        
        fact_rows = (await db.execute(
            select(FactRecord).where(FactRecord.document_id == doc.id)
        )).scalars().all()
        fact_map = {fact.fact_id: fact for fact in fact_rows}
        
        def fact_payload(fact_id: str) -> dict:
            record = fact_map.get(fact_id)
            if not record:
                return {
                    "fact_id": fact_id,
                    "content": "",
                    "fact_type": "",
                    "location": "文档开头",
                    "source_text": "",
                    "source_position": (0, 0),
                    "chapter": None,
                    "section": None,
                    "is_image_source": False,
                    "image_id": None,
                    "image_description": None,
                }
            # 从 fact_type 推断 is_image_source
            fact_type_str = record.fact_type or ""
            is_image_source = record.is_image_source or fact_type_str.startswith('image_')
            return {
                "fact_id": record.fact_id,
                "content": record.content,
                "fact_type": fact_type_str,
                "location": _format_location(record.chapter, record.section),
                "source_text": record.source_text,
                "source_position": (record.source_start, record.source_end),
                "chapter": record.chapter,
                "section": record.section,
                "is_image_source": is_image_source,
                "image_id": record.image_id,
                "image_description": record.image_description,
            }
        
        conflict_dicts = []
        for record in conflict_records:
            conflict_dict = {
                "conflict_id": record.conflict_id,
                "conflict_type": record.conflict_type,
                "severity": record.severity,
                "description": record.description,
                "suggestion": record.suggestion,
                "fact_a": fact_payload(record.fact_a_id),
                "fact_b": fact_payload(record.fact_b_id),
                "verification": None,
            }
            if record.is_verified is not None:
                conflict_dict["verification"] = {
                    "is_verified": record.is_verified,
                    "correct_fact": record.correct_fact,
                    "confidence": record.verification_confidence or 0.0,
                    "reasoning": record.verification_reasoning,
                }
            conflict_dicts.append(conflict_dict)
        
        return ConflictListResponse(
            task_id=task_id,
            total=total,
            conflicts=conflict_dicts,
        )
    
    conflicts = result.conflicts
    
    if conflict_type:
        conflicts = [c for c in conflicts if c.conflict.conflict_type.value == conflict_type]
    
    if min_severity > 0:
        conflicts = [c for c in conflicts if c.conflict.severity >= min_severity]
    
    total = len(conflicts)
    start = (page - 1) * page_size
    end = start + page_size
    conflicts = conflicts[start:end]
    
    conflict_dicts = []
    for c in conflicts:
        # 辅助函数：确保事实包含图片字段
        def ensure_fact_dict(fact):
            # 获取 fact_type 字符串
            fact_type_str = ""
            if hasattr(fact, 'fact_type'):
                if hasattr(fact.fact_type, 'value'):
                    fact_type_str = fact.fact_type.value
                else:
                    fact_type_str = str(fact.fact_type) if fact.fact_type else ""
            
            # 获取图片相关字段
            is_image_source = getattr(fact, 'is_image_source', None)
            image_id = getattr(fact, 'image_id', None)
            image_description = getattr(fact, 'image_description', None)
            
            # 如果 is_image_source 未设置，从 fact_type 推断
            if is_image_source is None:
                is_image_source = fact_type_str.startswith('image_') if fact_type_str else False
            
            fact_dict = {
                "fact_id": fact.fact_id,
                "content": fact.content,
                "fact_type": fact_type_str,  # 添加 fact_type 字段！
                "location": fact.location_description,
                "source_text": fact.source_text,
                "source_position": fact.source_position,
                "chapter": fact.chapter,
                "section": fact.section,
                "is_image_source": is_image_source or False,
                "image_id": image_id,
                "image_description": image_description,
            }
            
            # 调试日志
            if is_image_source or fact_type_str.startswith('image_'):
                logger.info(f"📸 事实 {fact.fact_id} 是图片来源，fact_type: {fact_type_str}, image_id: {image_id}")
            
            return fact_dict
        
        conflict_dict = {
            "conflict_id": c.conflict.conflict_id,
            "conflict_type": c.conflict.conflict_type.value,
            "severity": c.conflict.severity,
            "description": c.conflict.description,
            "suggestion": c.conflict.suggestion,
            "fact_a": ensure_fact_dict(c.conflict.fact_a),
            "fact_b": ensure_fact_dict(c.conflict.fact_b),
            "verification": None,
        }
        if c.verification:
            conflict_dict["verification"] = {
                "is_verified": c.verification.is_verified,
                "correct_fact": c.verification.correct_fact,
                "confidence": c.verification.confidence,
                "reasoning": c.verification.verification_reasoning,
            }
        conflict_dicts.append(conflict_dict)
    
    return ConflictListResponse(
        task_id=task_id,
        total=total,
        conflicts=conflict_dicts,
    )


@router.delete("/task/{task_id}", tags=["任务"])
async def delete_task(task_id: str):
    """
    删除任务及其相关数据
    """
    try:
        # 从内存中删除
        if task_id in _task_results:
            del _task_results[task_id]
        
        # 从Redis中删除
        try:
            redis_client = await get_redis_client()
            await redis_client.cleanup_task_data(task_id)
        except Exception:
            pass
        
        return {"message": "任务已删除", "task_id": task_id}
        
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.websocket("/ws/task/{task_id}/progress")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """
    WebSocket端点：实时获取任务进度
    """
    await websocket.accept()
    
    try:
        redis_client = await get_redis_client()
        pubsub = await redis_client.subscribe_progress(task_id)
        
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                data = json.loads(message["data"])
                await websocket.send_json(data)
                
                # 如果进度达到100%，关闭连接
                if data.get("progress", 0) >= 100:
                    break
            
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: task_id={task_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        try:
            await pubsub.unsubscribe()
        except Exception:
            pass


# ==================== 统计API ====================

@router.get("/stats/overview", tags=["统计"])
async def get_stats_overview(
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取系统统计概览（从数据库获取真实数据）
    """
    try:
        # 从数据库获取统计数据
        total_tasks_result = await db.execute(select(func.count(Document.id)))
        total_tasks = total_tasks_result.scalar() or 0
        
        completed_tasks_result = await db.execute(
            select(func.count(Document.id)).where(Document.status == "completed")
        )
        completed_tasks = completed_tasks_result.scalar() or 0
        
        total_facts_result = await db.execute(select(func.count(FactRecord.id)))
        total_facts = total_facts_result.scalar() or 0
        
        total_conflicts_result = await db.execute(select(func.count(ConflictRecord.id)))
        total_conflicts = total_conflicts_result.scalar() or 0
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "total_facts_extracted": total_facts,
            "total_conflicts_detected": total_conflicts,
        }
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        # 如果数据库查询失败，返回内存中的数据
        total_tasks = len(_task_results)
        completed_tasks = sum(1 for r in _task_results.values() if r)
        total_facts = sum(r.total_facts for r in _task_results.values() if r)
        total_conflicts = sum(r.total_conflicts for r in _task_results.values() if r)
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "total_facts_extracted": total_facts,
            "total_conflicts_detected": total_conflicts,
        }


@router.get("/stats/detailed", tags=["统计"])
async def get_stats_detailed(
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取详细统计数据（用于仪表盘图表）
    """
    try:
        # 冲突类型分布
        conflict_type_result = await db.execute(
            select(ConflictRecord.conflict_type, func.count(ConflictRecord.id))
            .group_by(ConflictRecord.conflict_type)
        )
        conflict_type_data = [
            {"name": row[0], "value": row[1]} for row in conflict_type_result.fetchall()
        ]
        
        # 冲突类型中文映射
        type_name_map = {
            "numerical": "数值冲突",
            "temporal": "时间冲突",
            "entity": "实体冲突",
            "categorical": "类别冲突",
            "definition": "定义冲突",
            "logical": "逻辑冲突",
            "spatial": "空间冲突",
        }
        for item in conflict_type_data:
            item["name"] = type_name_map.get(item["name"], item["name"])
        
        # 严重程度分布
        severity_ranges = [
            ("严重", 0.9, 1.0),
            ("较高", 0.6, 0.9),
            ("中等", 0.3, 0.6),
            ("轻微", 0.0, 0.3),
        ]
        severity_data = []
        for name, low, high in severity_ranges:
            result = await db.execute(
                select(func.count(ConflictRecord.id))
                .where(ConflictRecord.severity >= low)
                .where(ConflictRecord.severity < high)
            )
            count = result.scalar() or 0
            severity_data.append({"name": name, "count": count})
        
        # 最近7天趋势
        from datetime import timedelta
        today = datetime.now().date()
        trend_data = []
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            
            # 当天任务数
            task_result = await db.execute(
                select(func.count(Document.id))
                .where(func.date(Document.created_at) == date)
            )
            tasks = task_result.scalar() or 0
            
            # 当天冲突数
            conflict_result = await db.execute(
                select(func.count(ConflictRecord.id))
                .where(func.date(ConflictRecord.created_at) == date)
            )
            conflicts = conflict_result.scalar() or 0
            
            trend_data.append({
                "date": weekday_names[date.weekday()],
                "tasks": tasks,
                "conflicts": conflicts,
            })
        
        return {
            "conflict_type_distribution": conflict_type_data,
            "severity_distribution": severity_data,
            "weekly_trend": trend_data,
        }
    except Exception as e:
        logger.error(f"获取详细统计数据失败: {e}")
        # 返回空数据
        return {
            "conflict_type_distribution": [],
            "severity_distribution": [],
            "weekly_trend": [],
        }


# ==================== 用户分析历史 API ====================

@router.get("/user/analysis-history", tags=["用户"])
async def get_user_analysis_history(
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    page: int = 1,
    page_size: int = 20,
):
    """
    获取用户的分析历史记录
    """
    if not current_user:
        # 未登录用户返回空列表
        return {
            "records": [],
            "total": 0,
            "stats": {
                "total_analyses": 0,
                "completed_analyses": 0,
                "total_facts_extracted": 0,
                "total_conflicts_found": 0,
            },
        }
    
    try:
        # 查询用户的分析记录
        # 使用 PostgreSQL 的 ->> 操作符提取 JSON 文本值（通过 func.jsonb_extract_path_text）
        user_id_condition = func.jsonb_extract_path_text(Document.doc_metadata, 'user_id') == current_user.user_id

        # 协作房间（创建/参与）对应的文档也纳入统计
        owned_rooms_result = await db.execute(
            select(CollaborationRoom.room_id).where(CollaborationRoom.owner_id == current_user.id)
        )
        owned_room_ids = [row[0] for row in owned_rooms_result.all()]

        member_rooms_result = await db.execute(
            select(CollaborationRoom.room_id)
            .join(RoomMembership, RoomMembership.room_id == CollaborationRoom.id)
            .where(RoomMembership.user_id == current_user.id)
        )
        member_room_ids = [row[0] for row in member_rooms_result.all()]

        room_ids = list({room_id for room_id in owned_room_ids + member_room_ids if room_id})
        if room_ids:
            room_condition = func.jsonb_extract_path_text(Document.doc_metadata, 'room_id').in_(room_ids)
            doc_access_condition = or_(user_id_condition, room_condition)
        else:
            doc_access_condition = user_id_condition
        
        query = (
            select(Document)
            .where(doc_access_condition)
            .order_by(Document.created_at.desc())
        )
        
        # 分页
        offset = (page - 1) * page_size
        result = await db.execute(query.offset(offset).limit(page_size))
        documents = result.scalars().all()
        
        # 获取总数
        count_query = select(func.count(Document.id)).where(doc_access_condition)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 获取用户统计 - 注意累计统计需要包含所有分析记录
        stats_query = (
            select(
                func.count(Document.id),
                func.coalesce(func.sum(Document.total_facts), 0),
                func.coalesce(func.sum(Document.total_conflicts), 0),
            )
            .where(doc_access_condition)
        )
        stats_result = await db.execute(stats_query)
        stats_row = stats_result.fetchone()
        
        completed_query = select(func.count(Document.id)).where(
            doc_access_condition,
            Document.status == "completed",
        )
        completed_result = await db.execute(completed_query)
        completed_count = completed_result.scalar() or 0
        
        records = [
            {
                "task_id": doc.task_id,
                "title": doc.title,
                "content_length": doc.content_length,
                "status": doc.status,
                "total_facts": doc.total_facts,
                "total_conflicts": doc.total_conflicts,
                "analysis_time": doc.analysis_time,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
            }
            for doc in documents
        ]
        
        return {
            "records": records,
            "total": total,
            "stats": {
                "total_analyses": stats_row[0] or 0 if stats_row else 0,
                "completed_analyses": completed_count,
                "total_facts_extracted": stats_row[1] or 0 if stats_row else 0,
                "total_conflicts_found": stats_row[2] or 0 if stats_row else 0,
            },
        }
    except Exception as e:
        logger.error(f"获取用户分析历史失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "records": [],
            "total": 0,
            "stats": {
                "total_analyses": 0,
                "completed_analyses": 0,
                "total_facts_extracted": 0,
                "total_conflicts_found": 0,
            },
        }


# ==================== 用户仪表盘统计 API ====================

@router.get("/user/dashboard-stats", tags=["用户"])
async def get_user_dashboard_stats(
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户仪表盘统计数据
    - 用户参与的所有文档统计
    - 用户的协作房间统计
    """
    if not current_user:
        return {
            "user_stats": {
                "total_documents": 0,
                "total_facts": 0,
                "total_conflicts": 0,
                "completed_analyses": 0,
            },
            "collaboration_stats": {
                "rooms_created": 0,
                "rooms_joined": 0,
                "total_collaborations": 0,
            },
            "recent_activity": [],
        }
    
    try:
        # 用户文档统计 - 使用 PostgreSQL jsonb_extract_path_text 函数提取 JSON 值
        user_id_condition = func.jsonb_extract_path_text(Document.doc_metadata, 'user_id') == current_user.user_id
        
        doc_stats_query = (
            select(
                func.count(Document.id),
                func.coalesce(func.sum(Document.total_facts), 0),
                func.coalesce(func.sum(Document.total_conflicts), 0),
            )
            .where(user_id_condition)
        )
        doc_stats_result = await db.execute(doc_stats_query)
        doc_stats = doc_stats_result.fetchone()
        
        completed_query = select(func.count(Document.id)).where(
            func.jsonb_extract_path_text(Document.doc_metadata, 'user_id') == current_user.user_id,
            Document.status == "completed",
        )
        completed_result = await db.execute(completed_query)
        completed_count = completed_result.scalar() or 0
        
        # 协作房间统计 (使用数据库主键ID而不是字符串user_id)
        created_rooms_query = select(func.count(CollaborationRoom.id)).where(
            CollaborationRoom.owner_id == current_user.id
        )
        created_result = await db.execute(created_rooms_query)
        rooms_created = created_result.scalar() or 0
        
        joined_rooms_query = select(func.count(RoomMembership.id)).where(
            RoomMembership.user_id == current_user.id
        )
        joined_result = await db.execute(joined_rooms_query)
        rooms_joined = joined_result.scalar() or 0
        
        # 最近活动
        recent_docs_query = (
            select(Document)
            .where(func.jsonb_extract_path_text(Document.doc_metadata, 'user_id') == current_user.user_id)
            .order_by(Document.created_at.desc())
            .limit(5)
        )
        recent_docs_result = await db.execute(recent_docs_query)
        recent_docs = recent_docs_result.scalars().all()
        
        recent_activity = [
            {
                "type": "analysis",
                "title": doc.title or "未命名文档",
                "task_id": doc.task_id,
                "status": doc.status,
                "total_facts": doc.total_facts or 0,
                "total_conflicts": doc.total_conflicts or 0,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in recent_docs
        ]
        
        return {
            "user_stats": {
                "total_documents": doc_stats[0] or 0 if doc_stats else 0,
                "total_facts": int(doc_stats[1]) if doc_stats else 0,
                "total_conflicts": int(doc_stats[2]) if doc_stats else 0,
                "completed_analyses": completed_count,
            },
            "collaboration_stats": {
                "rooms_created": rooms_created,
                "rooms_joined": rooms_joined,
                "total_collaborations": rooms_created + rooms_joined,
            },
            "recent_activity": recent_activity,
        }
    except Exception as e:
        logger.error(f"获取用户仪表盘统计失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "user_stats": {
                "total_documents": 0,
                "total_facts": 0,
                "total_conflicts": 0,
                "completed_analyses": 0,
            },
            "collaboration_stats": {
                "rooms_created": 0,
                "rooms_joined": 0,
                "total_collaborations": 0,
            },
            "recent_activity": [],
        }


# ==================== 文档原文和导出 API ====================

@router.get("/task/{task_id}/document", tags=["任务"])
async def get_task_document(
    task_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取任务的文档原文（用于结果页面显示）
    """
    # 先从内存获取
    if task_id in _task_documents:
        return _task_documents[task_id]
    
    # 从数据库获取
    try:
        result = await db.execute(
            select(Document).where(Document.task_id == task_id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return {
            "content": doc.content,
            "title": doc.title,
            "content_json": doc.content_json if doc.content_json else None,
            "content_html": doc.content_html if doc.content_html else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档原文失败: {e}")
        raise HTTPException(status_code=500, detail="获取文档失败")


@router.put("/task/{task_id}/document", tags=["任务"])
async def update_task_document(
    task_id: str,
    request: dict,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    更新任务的文档内容（用于保存编辑后的文档）
    
    请求体:
    - content: 文档纯文本内容
    - content_json: 文档富文本JSON格式（可选）
    - title: 文档标题（可选）
    """
    from ..services.document_editor import RichTextContent
    
    try:
        # 从数据库获取文档
        result = await db.execute(
            select(Document).where(Document.task_id == task_id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 更新文档内容
        content = request.get("content", doc.content)
        content_json = request.get("content_json", doc.content_json)
        title = request.get("title", doc.title)
        
        # 处理富文本内容
        if content_json:
            content_html = RichTextContent.to_html(content_json)
            # 如果没有提供纯文本content，从content_json提取
            if not content or content == doc.content:
                content = RichTextContent.to_plain_text(content_json)
        else:
            # 如果没有提供content_json，从纯文本生成
            content_json = RichTextContent.from_plain_text(content)
            content_html = RichTextContent.to_html(content_json)
        
        # 更新数据库记录
        doc.content = content
        doc.content_json = content_json
        doc.content_html = content_html
        doc.content_length = len(content)
        doc.title = title or doc.title
        doc.updated_at = datetime.now()
        
        # 更新内存缓存
        _task_documents[task_id] = {
            "content": content,
            "title": doc.title,
            "content_json": content_json,
            "content_html": content_html,
        }
        
        await db.commit()
        
        logger.info(f"文档内容已更新: task_id={task_id}")
        
        return {
            "success": True,
            "message": "文档已保存",
            "content": content,
            "content_json": content_json,
            "title": doc.title,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文档内容失败: {e}")
        import traceback
        traceback.print_exc()
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新文档失败: {str(e)}")


@router.post("/task/{task_id}/reanalyze", response_model=AnalyzeResponse, tags=["任务"])
async def reanalyze_task_document(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    重新分析任务的文档（用于检测冲突）
    
    从数据库获取文档的最新内容，重新进行分析，更新冲突列表和事实列表
    """
    try:
        # 从数据库获取文档
        result = await db.execute(
            select(Document).where(Document.task_id == task_id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 获取文档内容
        content = doc.content
        content_json = doc.content_json
        title = doc.title
        
        # 计算文档内容哈希
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # 检查是否有相同文档正在分析
        is_analyzing, existing_task_id = await is_document_analyzing(content_hash)
        if is_analyzing and existing_task_id != task_id:
            raise HTTPException(
                status_code=409,
                detail=f"该文档正在分析中，任务ID: {existing_task_id}。请等待分析完成后再试。"
            )
        
        # 使用增强版分析引擎（支持图片处理和LangGraph优化）
        from ..services.analysis_engine import get_enhanced_analysis_engine
        engine = get_enhanced_analysis_engine()
        document = DocumentInput(
            content=content,
            title=title,
        )
        
        # 获取分析锁
        lock_acquired = await acquire_analysis_lock(content_hash, task_id)
        if not lock_acquired and existing_task_id != task_id:
            raise HTTPException(
                status_code=409,
                detail="该文档正在分析中，请等待分析完成后再试。"
            )
        
        # 保存用户ID以便后续关联
        user_id = current_user.user_id if current_user else None
        
        # 在后台执行分析
        async def run_reanalysis():
            try:
                redis_client = await get_redis_client()
                
                async def progress_callback(tid: str, progress: float, step: str):
                    await redis_client.update_task_progress(tid, progress, step)
                
                result = await engine.analyze_document(
                    document=document,
                    task_id=task_id,
                    progress_callback=progress_callback,
                    skip_verification=False,  # 重新分析时不跳过验证
                    content_json=content_json,
                )
                
                # 保存结果到内存
                _task_results[task_id] = result
                
                # 更新内存中的文档
                from ..services.document_editor import RichTextContent
                content_html = RichTextContent.to_html(content_json) if content_json else ""
                _task_documents[task_id] = {
                    "content": content,
                    "title": title,
                    "content_json": content_json,
                    "content_html": content_html,
                }
                
                # 清理旧的事实和冲突记录（删除后重新保存）
                # 需要重新获取doc.id，因为在后台任务中db会话可能已过期
                from ..utils.db_session import async_session_maker
                from sqlalchemy import delete
                
                async with async_session_maker() as db_session:
                    doc_result = await db_session.execute(
                        select(Document).where(Document.task_id == task_id)
                    )
                    current_doc = doc_result.scalar_one_or_none()
                    
                    if current_doc:
                        # 删除旧的事实记录
                        await db_session.execute(
                            delete(FactRecord).where(FactRecord.document_id == current_doc.id)
                        )
                        
                        # 删除旧的冲突记录
                        await db_session.execute(
                            delete(ConflictRecord).where(ConflictRecord.document_id == current_doc.id)
                        )
                        
                        await db_session.commit()
                
                # 保存新的分析结果到数据库（会在save_analysis_to_db中保存新的记录）
                await save_analysis_to_db(
                    task_id,
                    content,
                    title,
                    result,
                    user_id,
                    content_json=content_json
                )
                
                # 更新文档状态
                from ..utils.db_session import async_session_maker
                
                async with async_session_maker() as db_session:
                    doc_result = await db_session.execute(
                        select(Document).where(Document.task_id == task_id)
                    )
                    current_doc = doc_result.scalar_one_or_none()
                    
                    if current_doc:
                        current_doc.status = "completed"
                        current_doc.progress = 100.0
                        current_doc.total_facts = result.total_facts
                        current_doc.total_conflicts = result.total_conflicts
                        current_doc.analysis_time = result.analysis_time
                        current_doc.completed_at = datetime.now()
                        await db_session.commit()
                
                # 更新Redis中的任务状态
                await redis_client.save_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "current_step": "完成",
                })
                
                logger.info(f"重新分析完成: task_id={task_id}, facts={result.total_facts}, conflicts={result.total_conflicts}")
                
            except Exception as e:
                logger.error(f"重新分析任务 {task_id} 失败: {e}")
                import traceback
                traceback.print_exc()
                try:
                    redis_client = await get_redis_client()
                    await redis_client.save_task(task_id, {
                        "status": "failed",
                        "progress": 0,
                        "current_step": "失败",
                        "error_message": str(e),
                    })
                    doc.status = "failed"
                    await db.commit()
                except Exception:
                    pass
            finally:
                # 释放锁
                await release_analysis_lock(content_hash)
        
        # 初始化任务状态
        try:
            redis_client = await get_redis_client()
            await redis_client.save_task(task_id, {
                "status": "analyzing",
                "progress": 0,
                "current_step": "等待处理",
            })
            doc.status = "analyzing"
            doc.progress = 0.0
            await db.commit()
        except Exception as e:
            logger.warning(f"初始化重新分析任务状态失败: {e}")
        
        # 启动后台任务
        background_tasks.add_task(run_reanalysis)
        
        return AnalyzeResponse(
            task_id=task_id,
            status="analyzing",
            message="重新分析已启动",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动重新分析失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"启动重新分析失败: {str(e)}")


@router.get("/task/{task_id}/document/export", tags=["任务"])
async def export_task_document(
    task_id: str,
    format: str = Query("txt", description="导出格式: txt, md, pdf, docx"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    导出任务文档原文（支持富文本格式）
    
    支持格式：
    - txt: 纯文本
    - md: Markdown 格式
    - pdf: PDF 格式（保留格式和图片）
    - docx: Word 文档格式（保留格式和图片）
    """
    from ..services.document_editor import RichTextContent, get_document_editor
    
    try:
        # 从数据库获取文档
        result = await db.execute(
            select(Document).where(Document.task_id == task_id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        editor = get_document_editor()
        title = doc.title or "未命名文档"
        
        # 获取富文本内容（优先使用 content_json）
        content_json = doc.content_json if doc.content_json else RichTextContent.from_plain_text(doc.content)
        
        # 处理文件名编码（支持中文）
        import urllib.parse
        import re
        # 清理文件名（移除特殊字符，保留中英文、数字、空格、横线、下划线）
        clean_title = re.sub(r'[^\w\s\u4e00-\u9fff\-]', '', title).strip() or 'document'
        # 使用 RFC 5987 编码方式，确保中文文件名正确显示
        # quote() 需要字符串，不是字节，使用 encoding='utf-8' 参数
        encoded_filename = urllib.parse.quote(clean_title, safe='', encoding='utf-8')
        
        # 备用ASCII文件名（必须是纯ASCII，HTTP响应头要求）
        ascii_fallback_raw = clean_title.encode('ascii', 'ignore').decode('ascii').strip()
        if ascii_fallback_raw and ascii_fallback_raw == clean_title:
            # 如果标题本身就是ASCII，直接使用
            ascii_fallback = clean_title[:50] if len(clean_title) > 50 else clean_title
        else:
            # 如果包含中文，使用一个纯ASCII的后备名
            # 限制长度并确保是纯ASCII
            ascii_fallback = 'document'  # 使用固定后备名，浏览器会使用 filename* 参数
        
        if format == "txt":
            # 纯文本格式
            content = RichTextContent.to_plain_text(content_json, include_image_placeholders=True)
            return Response(
                content=content,
                media_type="text/plain; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{ascii_fallback}.txt"; filename*=UTF-8\'\'{encoded_filename}.txt',
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        
        elif format == "md":
            # Markdown 格式
            content = editor.convert_to_markdown(content_json)
            return Response(
                content=content,
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{ascii_fallback}.md"; filename*=UTF-8\'\'{encoded_filename}.md',
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        
        elif format == "pdf":
            # PDF 格式
            try:
                pdf_content = await editor.convert_to_pdf(content_json, title)
                return Response(
                    content=pdf_content,
                    media_type="application/pdf",
                    status_code=200,
                    headers={
                        "Content-Disposition": f'attachment; filename="{ascii_fallback}.pdf"; filename*=UTF-8\'\'{encoded_filename}.pdf',
                        "Cache-Control": "no-cache, no-store, must-revalidate, private",
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "X-Content-Type-Options": "nosniff"
                    }
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"PDF导出失败: {e}")
                raise HTTPException(status_code=500, detail=f"PDF导出失败: {str(e)}")
        
        elif format == "docx":
            # DOCX 格式
            try:
                docx_content = await editor.convert_to_docx(content_json, title)
                return Response(
                    content=docx_content,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    status_code=200,
                    headers={
                        "Content-Disposition": f'attachment; filename="{ascii_fallback}.docx"; filename*=UTF-8\'\'{encoded_filename}.docx',
                        "Cache-Control": "no-cache, no-store, must-revalidate, private",
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "X-Content-Type-Options": "nosniff"
                    }
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"DOCX导出失败: {e}")
                raise HTTPException(status_code=500, detail=f"DOCX导出失败: {str(e)}")
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的导出格式: {format}，支持的格式有: txt, md, pdf, docx"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/parse-document", tags=["文档"])
async def parse_document_file(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    解析文档文件（PDF、DOCX、MD、TXT），提取格式和图片，转换为富文本 JSON
    
    支持格式：
    - txt: 纯文本
    - md: Markdown（支持加粗、斜体、标题、列表、链接、图片等）
    - docx: Word文档（支持格式、图片）
    - pdf: PDF文档（目前仅提取文本，格式信息可能丢失）
    
    Returns:
        包含 content, content_json, title 的字典
    """
    from ..services.document_editor import get_document_editor
    
    try:
        # 读取文件内容
        file_content = await file.read()
        filename = file.filename or "document"
        mime_type = file.content_type or ""
        
        # 获取用户ID（可选）
        # 注意：User模型同时有 id (Integer) 和 user_id (String) 两个字段
        user_id = None
        if current_user:
            # User模型的 id 是 Integer 类型的主键，user_id 是 String 类型的唯一标识
            # 图片上传需要使用 Integer 类型的 id
            user_id = current_user.id
            logger.info(f"解析文档: 用户ID={user_id}, username={current_user.username}")
        else:
            logger.warning("解析文档: current_user为None，可能用户未登录或token无效，图片将无法上传")
        
        # 解析文件
        editor = get_document_editor()
        result = await editor.parse_document_file(
            file_content=file_content,
            filename=filename,
            mime_type=mime_type,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "content": result["content"],
            "content_json": result["content_json"],
            "title": result["title"],
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"解析文档失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.get("/task/{task_id}/export", tags=["任务"])
async def export_task_report(
    task_id: str,
    format: str = Query("markdown", description="导出格式: markdown/md, json, pdf, docx, txt"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    导出分析报告
    
    支持格式：
    - markdown/md: Markdown 格式
    - json: JSON 格式
    - pdf: PDF 格式（带格式和样式）
    - docx: Word 文档格式
    - txt: 纯文本格式
    
    报告包含：
    - 文档概览信息
    - 完整的冲突列表（含详细描述、事实对比、修正建议）
    - 完整的事实列表
    """
    result = _task_results.get(task_id)
    
    # 获取事实 ID 到事实内容的映射（从数据库）
    fact_map = {}
    
    # 如果内存没有，从数据库加载
    if not result:
        try:
            doc_result = await db.execute(
                select(Document).where(Document.task_id == task_id)
            )
            doc = doc_result.scalar_one_or_none()
            if not doc:
                raise HTTPException(status_code=404, detail="结果不存在")
            
            # 获取所有事实记录
            facts_result = await db.execute(
                select(FactRecord).where(FactRecord.document_id == doc.id)
            )
            facts = facts_result.scalars().all()
            
            # 构建事实映射
            for f in facts:
                fact_map[f.fact_id] = {
                    "fact_id": f.fact_id,
                    "content": f.content,
                    "fact_type": f.fact_type,
                    "confidence": f.confidence,
                    "source_text": f.source_text,
                    "chapter": f.chapter,
                    "section": f.section,
                    "location": _format_location(f.chapter, f.section),
                }
            
            # 获取冲突记录
            conflicts_result = await db.execute(
                select(ConflictRecord).where(ConflictRecord.document_id == doc.id)
            )
            conflicts = conflicts_result.scalars().all()
            
            # 组装完整的冲突数据（包含事实详情）
            conflicts_data = []
            for c in conflicts:
                fact_a = fact_map.get(c.fact_a_id, {"fact_id": c.fact_a_id, "content": "未找到", "location": "未知"})
                fact_b = fact_map.get(c.fact_b_id, {"fact_id": c.fact_b_id, "content": "未找到", "location": "未知"})
                
                conflicts_data.append({
                    "conflict_id": c.conflict_id,
                    "conflict_type": c.conflict_type,
                    "severity": c.severity,
                    "description": c.description,
                    "suggestion": c.suggestion,
                    "is_verified": c.is_verified,
                    "correct_fact": c.correct_fact,
                    "verification_reasoning": c.verification_reasoning,
                    "verification_confidence": c.verification_confidence,
                    "source_description": c.source_description,
                    "fact_a": fact_a,
                    "fact_b": fact_b,
                })
            
            # 组装报告数据
            report_data = {
                "task_id": task_id,
                "title": doc.title or "未命名文档",
                "document_length": doc.content_length,
                "total_facts": doc.total_facts,
                "total_conflicts": doc.total_conflicts,
                "analysis_time": doc.analysis_time,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
                "facts": list(fact_map.values()),
                "conflicts": conflicts_data,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"导出报告失败: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail="导出失败")
    else:
        # 从内存结果组装
        # 构建事实映射
        for f in result.facts:
            fact_map[f.fact_id] = {
                "fact_id": f.fact_id,
                "content": f.content,
                "fact_type": f.fact_type,
                "confidence": f.confidence,
                "source_text": f.source_text,
                "chapter": f.chapter,
                "section": f.section,
                "location": f.location_description,
            }
        
        # 组装完整的冲突数据
        conflicts_data = []
        for c in result.conflicts:
            conflicts_data.append({
                "conflict_id": c.conflict.conflict_id,
                "conflict_type": c.conflict.conflict_type.value,
                "severity": c.conflict.severity,
                "description": c.conflict.description,
                "suggestion": c.conflict.suggestion,
                "is_verified": c.verification is not None and c.verification.is_verified,
                "correct_fact": c.verification.correct_fact if c.verification else None,
                "verification_reasoning": c.verification.verification_reasoning if c.verification else None,
                "verification_confidence": c.verification.confidence if c.verification else None,
                "source_description": c.verification.source_description if c.verification else None,
                "fact_a": {
                    "fact_id": c.conflict.fact_a.fact_id,
                    "content": c.conflict.fact_a.content,
                    "fact_type": c.conflict.fact_a.fact_type,
                    "source_text": c.conflict.fact_a.source_text,
                    "location": c.conflict.fact_a.location_description,
                    "chapter": c.conflict.fact_a.chapter,
                    "section": c.conflict.fact_a.section,
                },
                "fact_b": {
                    "fact_id": c.conflict.fact_b.fact_id,
                    "content": c.conflict.fact_b.content,
                    "fact_type": c.conflict.fact_b.fact_type,
                    "source_text": c.conflict.fact_b.source_text,
                    "location": c.conflict.fact_b.location_description,
                    "chapter": c.conflict.fact_b.chapter,
                    "section": c.conflict.fact_b.section,
                },
            })
        
        report_data = {
            "task_id": result.task_id,
            "title": result.document_title or "未命名文档",
            "document_length": result.document_length,
            "total_facts": result.total_facts,
            "total_conflicts": result.total_conflicts,
            "analysis_time": result.analysis_time,
            "created_at": datetime.now().isoformat(),
            "facts": list(fact_map.values()),
            "conflicts": conflicts_data,
        }
    
    # 处理文件名编码
    import urllib.parse
    import re
    clean_title = re.sub(r'[^\w\s\u4e00-\u9fff\-]', '', report_data['title']).strip() or 'report'
    encoded_filename = urllib.parse.quote(clean_title, safe='', encoding='utf-8')
    ascii_fallback = 'report'
    
    if format == "json":
        return Response(
            content=json.dumps(report_data, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{ascii_fallback}_report.json"; filename*=UTF-8\'\'{encoded_filename}_report.json'
            },
        )
    
    elif format in ("markdown", "md"):
        # 生成 Markdown 报告（完整版）
        md_content = generate_markdown_report(report_data, include_full_facts=True)
        return Response(
            content=md_content,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{ascii_fallback}_report.md"; filename*=UTF-8\'\'{encoded_filename}_report.md'
            },
        )
    
    elif format == "txt":
        # 生成纯文本报告
        txt_content = generate_txt_report(report_data)
        return Response(
            content=txt_content,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{ascii_fallback}_report.txt"; filename*=UTF-8\'\'{encoded_filename}_report.txt'
            },
        )
    
    elif format == "pdf":
        # 生成 PDF 报告
        try:
            pdf_content = await generate_pdf_report(report_data)
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{ascii_fallback}_report.pdf"; filename*=UTF-8\'\'{encoded_filename}_report.pdf',
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
            )
        except Exception as e:
            logger.error(f"生成PDF报告失败: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"生成PDF报告失败: {str(e)}")
    
    elif format == "docx":
        # 生成 DOCX 报告
        try:
            docx_content = await generate_docx_report(report_data)
            return Response(
                content=docx_content,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="{ascii_fallback}_report.docx"; filename*=UTF-8\'\'{encoded_filename}_report.docx',
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
            )
        except Exception as e:
            logger.error(f"生成DOCX报告失败: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"生成DOCX报告失败: {str(e)}")
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的导出格式: {format}，支持的格式有: markdown/md, json, pdf, docx, txt"
        )


def generate_markdown_report(data: dict, include_full_facts: bool = False) -> str:
    """
    生成Markdown格式报告
    
    Args:
        data: 报告数据
        include_full_facts: 是否包含完整事实列表（默认False只显示前50条）
    """
    # 冲突类型中文映射
    type_map = {
        "numerical": "数值冲突",
        "temporal": "时间冲突",
        "entity": "实体冲突",
        "categorical": "类别冲突",
        "definition": "定义冲突",
        "logical": "逻辑冲突",
        "spatial": "空间冲突",
    }
    
    # 事实类型中文映射
    fact_type_map = {
        "numerical": "数值事实",
        "temporal": "时间事实",
        "entity": "实体事实",
        "categorical": "类别事实",
        "definition": "定义事实",
        "relationship": "关系事实",
        "location": "位置事实",
        "other": "其他事实",
    }
    
    lines = [
        f"# {data['title']} - 分析报告",
        "",
        "## 📊 文档概览",
        "",
        "| 项目 | 内容 |",
        "|------|------|",
        f"| 任务ID | `{data['task_id']}` |",
        f"| 文档长度 | {data['document_length']:,} 字 |",
        f"| 提取事实 | {data['total_facts']} 条 |",
        f"| 发现冲突 | {data['total_conflicts']} 处 |",
        f"| 分析耗时 | {data.get('analysis_time', 0):.1f} 秒 |",
        f"| 生成时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
        "",
    ]
    
    # 冲突详情（完整列表）
    if data.get("conflicts"):
        lines.extend([
            "---",
            "",
            "## ⚠️ 冲突详情",
            "",
            f"共发现 **{len(data['conflicts'])}** 处冲突：",
            "",
        ])
        
        for i, conflict in enumerate(data["conflicts"], 1):
            severity = conflict["severity"]
            severity_level = (
                "🔴 严重" if severity >= 0.9 else
                "🟠 较高" if severity >= 0.6 else
                "🟡 中等" if severity >= 0.3 else
                "🟢 轻微"
            )
            severity_percent = f"{severity * 100:.0f}%"
            
            conflict_type_cn = type_map.get(conflict['conflict_type'], conflict['conflict_type'])
            
            lines.extend([
                f"### {i}. {conflict_type_cn} ({severity_level} - {severity_percent})",
                "",
                f"**冲突描述**：{conflict['description']}",
                "",
            ])
            
            # 事实对比
            if conflict.get("fact_a") and conflict.get("fact_b"):
                fact_a = conflict["fact_a"]
                fact_b = conflict["fact_b"]
                
                lines.extend([
                    "#### 事实对比",
                    "",
                    "| | 事实A | 事实B |",
                    "|---|-------|-------|",
                    f"| **内容** | {fact_a.get('content', '未知')} | {fact_b.get('content', '未知')} |",
                    f"| **位置** | {fact_a.get('location', '未知')} | {fact_b.get('location', '未知')} |",
                ])
                
                # 添加原文引用（如果有）
                if fact_a.get('source_text') or fact_b.get('source_text'):
                    source_a = fact_a.get('source_text', '-')[:100] + ('...' if len(fact_a.get('source_text', '')) > 100 else '')
                    source_b = fact_b.get('source_text', '-')[:100] + ('...' if len(fact_b.get('source_text', '')) > 100 else '')
                    lines.append(f"| **原文** | {source_a} | {source_b} |")
                
                lines.append("")
            
            # 修正建议
            if conflict.get("suggestion"):
                lines.extend([
                    f"**💡 修正建议**：{conflict['suggestion']}",
                    "",
                ])
            
            # 验证结果
            if conflict.get("is_verified"):
                lines.extend([
                    "#### ✅ 验证结果",
                    "",
                ])
                if conflict.get("correct_fact"):
                    lines.append(f"**正确事实**：{conflict['correct_fact']}")
                if conflict.get("verification_reasoning"):
                    lines.append(f"**验证推理**：{conflict['verification_reasoning']}")
                if conflict.get("verification_confidence"):
                    lines.append(f"**置信度**：{conflict['verification_confidence'] * 100:.0f}%")
                if conflict.get("source_description"):
                    lines.append(f"**来源说明**：{conflict['source_description']}")
                lines.append("")
            
            lines.append("")
    
    # 事实列表（完整）
    if data.get("facts"):
        lines.extend([
            "---",
            "",
            "## 📝 事实列表",
            "",
            f"共提取 **{len(data['facts'])}** 条事实：",
            "",
        ])
        
        facts_to_show = data["facts"] if include_full_facts else data["facts"][:100]
        
        # 按类型分组
        facts_by_type = {}
        for fact in facts_to_show:
            ft = fact.get("fact_type", "other")
            if ft not in facts_by_type:
                facts_by_type[ft] = []
            facts_by_type[ft].append(fact)
        
        for fact_type, facts in facts_by_type.items():
            type_name = fact_type_map.get(fact_type, fact_type)
            lines.extend([
                f"### {type_name} ({len(facts)}条)",
                "",
                "| # | 内容 | 位置 | 置信度 |",
                "|---|------|------|--------|",
            ])
            
            for idx, fact in enumerate(facts, 1):
                content = fact.get("content", "")[:80]
                if len(fact.get("content", "")) > 80:
                    content += "..."
                location = fact.get("location", "-") or _format_location(fact.get("chapter"), fact.get("section"))
                confidence = f"{fact.get('confidence', 1.0) * 100:.0f}%"
                lines.append(f"| {idx} | {content} | {location} | {confidence} |")
            
            lines.append("")
        
        if not include_full_facts and len(data["facts"]) > 100:
            lines.append(f"*注：仅显示前100条事实，共{len(data['facts'])}条*")
            lines.append("")
    
    lines.extend([
        "---",
        "",
        "*本报告由 PatPat-Inconsistency-Hunter 自动生成*",
        "",
        f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ])
    
    return "\n".join(lines)


def generate_txt_report(data: dict) -> str:
    """生成纯文本格式报告"""
    # 冲突类型中文映射
    type_map = {
        "numerical": "数值冲突",
        "temporal": "时间冲突",
        "entity": "实体冲突",
        "categorical": "类别冲突",
        "definition": "定义冲突",
        "logical": "逻辑冲突",
        "spatial": "空间冲突",
    }
    
    fact_type_map = {
        "numerical": "数值事实",
        "temporal": "时间事实",
        "entity": "实体事实",
        "categorical": "类别事实",
        "definition": "定义事实",
        "relationship": "关系事实",
        "location": "位置事实",
        "other": "其他事实",
    }
    
    lines = [
        "=" * 60,
        f"  {data['title']} - 分析报告",
        "=" * 60,
        "",
        "【文档概览】",
        f"  任务ID: {data['task_id']}",
        f"  文档长度: {data['document_length']:,} 字",
        f"  提取事实: {data['total_facts']} 条",
        f"  发现冲突: {data['total_conflicts']} 处",
        f"  分析耗时: {data.get('analysis_time', 0):.1f} 秒",
        f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    
    # 冲突详情
    if data.get("conflicts"):
        lines.extend([
            "-" * 60,
            "【冲突详情】",
            "-" * 60,
            "",
        ])
        
        for i, conflict in enumerate(data["conflicts"], 1):
            severity = conflict["severity"]
            severity_level = (
                "[严重]" if severity >= 0.9 else
                "[较高]" if severity >= 0.6 else
                "[中等]" if severity >= 0.3 else
                "[轻微]"
            )
            
            conflict_type_cn = type_map.get(conflict['conflict_type'], conflict['conflict_type'])
            
            lines.extend([
                f"冲突 {i}: {conflict_type_cn} {severity_level}",
                f"  严重程度: {severity * 100:.0f}%",
                f"  描述: {conflict['description']}",
            ])
            
            if conflict.get("fact_a") and conflict.get("fact_b"):
                lines.extend([
                    "  事实A:",
                    f"    内容: {conflict['fact_a'].get('content', '未知')}",
                    f"    位置: {conflict['fact_a'].get('location', '未知')}",
                    "  事实B:",
                    f"    内容: {conflict['fact_b'].get('content', '未知')}",
                    f"    位置: {conflict['fact_b'].get('location', '未知')}",
                ])
            
            if conflict.get("suggestion"):
                lines.append(f"  修正建议: {conflict['suggestion']}")
            
            if conflict.get("is_verified") and conflict.get("correct_fact"):
                lines.append(f"  验证结果: {conflict['correct_fact']}")
            
            lines.append("")
    
    # 事实列表
    if data.get("facts"):
        lines.extend([
            "-" * 60,
            "【事实列表】",
            "-" * 60,
            "",
        ])
        
        for i, fact in enumerate(data["facts"], 1):
            type_name = fact_type_map.get(fact.get("fact_type", "other"), fact.get("fact_type", "其他"))
            location = fact.get("location", "-") or _format_location(fact.get("chapter"), fact.get("section"))
            
            lines.extend([
                f"事实 {i}: [{type_name}]",
                f"  内容: {fact.get('content', '')}",
                f"  位置: {location}",
                f"  置信度: {fact.get('confidence', 1.0) * 100:.0f}%",
            ])
            
            if fact.get("source_text"):
                source = fact["source_text"][:150]
                if len(fact["source_text"]) > 150:
                    source += "..."
                lines.append(f"  原文: {source}")
            
            lines.append("")
    
    lines.extend([
        "=" * 60,
        "  报告由 PatPat-Inconsistency-Hunter 自动生成",
        "=" * 60,
    ])
    
    return "\n".join(lines)


async def generate_pdf_report(data: dict) -> bytes:
    """生成PDF格式报告"""
    try:
        from weasyprint import HTML
        import html as html_escape
        
        # 冲突类型中文映射
        type_map = {
            "numerical": "数值冲突",
            "temporal": "时间冲突",
            "entity": "实体冲突",
            "categorical": "类别冲突",
            "definition": "定义冲突",
            "logical": "逻辑冲突",
            "spatial": "空间冲突",
        }
        
        fact_type_map = {
            "numerical": "数值事实",
            "temporal": "时间事实",
            "entity": "实体事实",
            "categorical": "类别事实",
            "definition": "定义事实",
            "relationship": "关系事实",
            "location": "位置事实",
            "other": "其他事实",
        }
        
        title = html_escape.escape(data['title'])
        
        # 构建冲突HTML
        conflicts_html = ""
        if data.get("conflicts"):
            conflicts_html = "<h2>⚠️ 冲突详情</h2>"
            
            for i, conflict in enumerate(data["conflicts"], 1):
                severity = conflict["severity"]
                severity_class = (
                    "critical" if severity >= 0.9 else
                    "high" if severity >= 0.6 else
                    "medium" if severity >= 0.3 else
                    "low"
                )
                severity_label = (
                    "严重" if severity >= 0.9 else
                    "较高" if severity >= 0.6 else
                    "中等" if severity >= 0.3 else
                    "轻微"
                )
                
                conflict_type_cn = type_map.get(conflict['conflict_type'], conflict['conflict_type'])
                description = html_escape.escape(conflict.get('description', ''))
                suggestion = html_escape.escape(conflict.get('suggestion', ''))
                
                conflicts_html += f'''
                <div class="conflict-item">
                    <h3>
                        <span class="conflict-num">{i}.</span>
                        {conflict_type_cn}
                        <span class="severity-badge {severity_class}">{severity_label} ({severity*100:.0f}%)</span>
                    </h3>
                    <p><strong>描述：</strong>{description}</p>
                '''
                
                if conflict.get("fact_a") and conflict.get("fact_b"):
                    fact_a = conflict["fact_a"]
                    fact_b = conflict["fact_b"]
                    conflicts_html += f'''
                    <table class="fact-compare">
                        <tr>
                            <th></th>
                            <th>事实A</th>
                            <th>事实B</th>
                        </tr>
                        <tr>
                            <td><strong>内容</strong></td>
                            <td>{html_escape.escape(str(fact_a.get('content', '未知')))}</td>
                            <td>{html_escape.escape(str(fact_b.get('content', '未知')))}</td>
                        </tr>
                        <tr>
                            <td><strong>位置</strong></td>
                            <td>{html_escape.escape(str(fact_a.get('location', '未知')))}</td>
                            <td>{html_escape.escape(str(fact_b.get('location', '未知')))}</td>
                        </tr>
                    </table>
                    '''
                
                if suggestion:
                    conflicts_html += f'<p class="suggestion"><strong>💡 修正建议：</strong>{suggestion}</p>'
                
                if conflict.get("is_verified") and conflict.get("correct_fact"):
                    correct_fact = html_escape.escape(conflict.get('correct_fact', ''))
                    conflicts_html += f'<p class="verified"><strong>✅ 验证结果：</strong>{correct_fact}</p>'
                
                conflicts_html += "</div>"
        
        # 构建事实HTML
        facts_html = ""
        if data.get("facts"):
            facts_html = f"<h2>📝 事实列表（共{len(data['facts'])}条）</h2>"
            facts_html += '''
            <table class="facts-table">
                <tr>
                    <th>#</th>
                    <th>类型</th>
                    <th>内容</th>
                    <th>位置</th>
                    <th>置信度</th>
                </tr>
            '''
            
            for idx, fact in enumerate(data["facts"], 1):
                type_name = fact_type_map.get(fact.get("fact_type", "other"), fact.get("fact_type", "其他"))
                content = html_escape.escape(fact.get("content", "")[:100])
                if len(fact.get("content", "")) > 100:
                    content += "..."
                location = html_escape.escape(fact.get("location", "-") or _format_location(fact.get("chapter"), fact.get("section")))
                confidence = f"{fact.get('confidence', 1.0) * 100:.0f}%"
                
                facts_html += f'''
                <tr>
                    <td>{idx}</td>
                    <td>{type_name}</td>
                    <td>{content}</td>
                    <td>{location}</td>
                    <td>{confidence}</td>
                </tr>
                '''
            
            facts_html += "</table>"
        
        # 完整HTML
        full_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title} - 分析报告</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
            @bottom-center {{
                content: counter(page) " / " counter(pages);
                font-size: 10pt;
                color: #666;
            }}
        }}
        
        @font-face {{
            font-family: "CJK";
            src: local("WenQuanYi Zen Hei"), local("Noto Sans CJK SC"), local("Microsoft YaHei"), local("SimHei");
        }}
        
        body {{
            font-family: "CJK", "WenQuanYi Zen Hei", "Microsoft YaHei", sans-serif;
            line-height: 1.6;
            color: #333;
            font-size: 11pt;
        }}
        
        h1 {{
            text-align: center;
            color: #1a1a1a;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        
        h2 {{
            color: #2c3e50;
            border-left: 4px solid #3498db;
            padding-left: 10px;
            margin-top: 30px;
        }}
        
        .overview-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        .overview-table td {{
            padding: 8px 12px;
            border: 1px solid #ddd;
        }}
        
        .overview-table td:first-child {{
            background: #f5f5f5;
            font-weight: bold;
            width: 120px;
        }}
        
        .conflict-item {{
            background: #fafafa;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
            page-break-inside: avoid;
        }}
        
        .conflict-item h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        
        .conflict-num {{
            color: #666;
        }}
        
        .severity-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10pt;
            margin-left: 10px;
        }}
        
        .severity-badge.critical {{ background: #ff4444; color: white; }}
        .severity-badge.high {{ background: #ff8800; color: white; }}
        .severity-badge.medium {{ background: #ffcc00; color: #333; }}
        .severity-badge.low {{ background: #00cc66; color: white; }}
        
        .fact-compare {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        
        .fact-compare th, .fact-compare td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        
        .fact-compare th {{
            background: #f0f0f0;
        }}
        
        .suggestion {{
            color: #2980b9;
            background: #ecf6fd;
            padding: 8px;
            border-radius: 3px;
        }}
        
        .verified {{
            color: #27ae60;
            background: #e8f8f0;
            padding: 8px;
            border-radius: 3px;
        }}
        
        .facts-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
        }}
        
        .facts-table th, .facts-table td {{
            border: 1px solid #ddd;
            padding: 6px 8px;
            text-align: left;
        }}
        
        .facts-table th {{
            background: #f0f0f0;
            font-weight: bold;
        }}
        
        .facts-table tr:nth-child(even) {{
            background: #fafafa;
        }}
        
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #888;
            font-size: 9pt;
            border-top: 1px solid #ddd;
            padding-top: 10px;
        }}
    </style>
</head>
<body>
    <h1>{title} - 分析报告</h1>
    
    <h2>📊 文档概览</h2>
    <table class="overview-table">
        <tr><td>任务ID</td><td>{data['task_id']}</td></tr>
        <tr><td>文档长度</td><td>{data['document_length']:,} 字</td></tr>
        <tr><td>提取事实</td><td>{data['total_facts']} 条</td></tr>
        <tr><td>发现冲突</td><td>{data['total_conflicts']} 处</td></tr>
        <tr><td>分析耗时</td><td>{data.get('analysis_time', 0):.1f} 秒</td></tr>
        <tr><td>生成时间</td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
    </table>
    
    {conflicts_html}
    
    {facts_html}
    
    <div class="footer">
        报告由 PatPat-Inconsistency-Hunter 自动生成<br>
        生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>'''
        
        html_doc = HTML(string=full_html, base_url=".")
        return html_doc.write_pdf()
        
    except ImportError:
        raise ValueError("PDF生成功能需要安装weasyprint库")


async def generate_docx_report(data: dict) -> bytes:
    """生成DOCX格式报告"""
    try:
        from docx import Document as DocxDocument
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        import io
        
        # 冲突类型中文映射
        type_map = {
            "numerical": "数值冲突",
            "temporal": "时间冲突",
            "entity": "实体冲突",
            "categorical": "类别冲突",
            "definition": "定义冲突",
            "logical": "逻辑冲突",
            "spatial": "空间冲突",
        }
        
        fact_type_map = {
            "numerical": "数值事实",
            "temporal": "时间事实",
            "entity": "实体事实",
            "categorical": "类别事实",
            "definition": "定义事实",
            "relationship": "关系事实",
            "location": "位置事实",
            "other": "其他事实",
        }
        
        doc = DocxDocument()
        
        # 标题
        title = doc.add_heading(f"{data['title']} - 分析报告", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 概览
        doc.add_heading("📊 文档概览", level=1)
        
        overview_table = doc.add_table(rows=6, cols=2)
        overview_table.style = 'Light Grid Accent 1'
        
        overview_data = [
            ("任务ID", data['task_id']),
            ("文档长度", f"{data['document_length']:,} 字"),
            ("提取事实", f"{data['total_facts']} 条"),
            ("发现冲突", f"{data['total_conflicts']} 处"),
            ("分析耗时", f"{data.get('analysis_time', 0):.1f} 秒"),
            ("生成时间", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ]
        
        for i, (label, value) in enumerate(overview_data):
            overview_table.rows[i].cells[0].text = label
            overview_table.rows[i].cells[1].text = str(value)
        
        # 冲突详情
        if data.get("conflicts"):
            doc.add_heading("⚠️ 冲突详情", level=1)
            doc.add_paragraph(f"共发现 {len(data['conflicts'])} 处冲突：")
            
            for i, conflict in enumerate(data["conflicts"], 1):
                severity = conflict["severity"]
                severity_label = (
                    "严重" if severity >= 0.9 else
                    "较高" if severity >= 0.6 else
                    "中等" if severity >= 0.3 else
                    "轻微"
                )
                
                conflict_type_cn = type_map.get(conflict['conflict_type'], conflict['conflict_type'])
                
                # 冲突标题
                heading = doc.add_heading(f"{i}. {conflict_type_cn} ({severity_label} - {severity*100:.0f}%)", level=2)
                
                # 描述
                doc.add_paragraph(f"描述：{conflict.get('description', '')}")
                
                # 事实对比表格
                if conflict.get("fact_a") and conflict.get("fact_b"):
                    fact_a = conflict["fact_a"]
                    fact_b = conflict["fact_b"]
                    
                    compare_table = doc.add_table(rows=3, cols=3)
                    compare_table.style = 'Light Grid'
                    
                    # 表头
                    compare_table.rows[0].cells[0].text = ""
                    compare_table.rows[0].cells[1].text = "事实A"
                    compare_table.rows[0].cells[2].text = "事实B"
                    
                    # 内容
                    compare_table.rows[1].cells[0].text = "内容"
                    compare_table.rows[1].cells[1].text = str(fact_a.get('content', '未知'))
                    compare_table.rows[1].cells[2].text = str(fact_b.get('content', '未知'))
                    
                    # 位置
                    compare_table.rows[2].cells[0].text = "位置"
                    compare_table.rows[2].cells[1].text = str(fact_a.get('location', '未知'))
                    compare_table.rows[2].cells[2].text = str(fact_b.get('location', '未知'))
                    
                    doc.add_paragraph()  # 空行
                
                # 修正建议
                if conflict.get("suggestion"):
                    p = doc.add_paragraph()
                    p.add_run("💡 修正建议：").bold = True
                    p.add_run(conflict['suggestion'])
                
                # 验证结果
                if conflict.get("is_verified") and conflict.get("correct_fact"):
                    p = doc.add_paragraph()
                    p.add_run("✅ 验证结果：").bold = True
                    p.add_run(conflict['correct_fact'])
                
                doc.add_paragraph()  # 空行分隔
        
        # 事实列表
        if data.get("facts"):
            doc.add_heading("📝 事实列表", level=1)
            doc.add_paragraph(f"共提取 {len(data['facts'])} 条事实：")
            
            # 创建事实表格
            facts_table = doc.add_table(rows=1, cols=5)
            facts_table.style = 'Light Grid Accent 1'
            
            # 表头
            header_cells = facts_table.rows[0].cells
            header_cells[0].text = "#"
            header_cells[1].text = "类型"
            header_cells[2].text = "内容"
            header_cells[3].text = "位置"
            header_cells[4].text = "置信度"
            
            # 数据行
            for idx, fact in enumerate(data["facts"], 1):
                row = facts_table.add_row()
                cells = row.cells
                
                type_name = fact_type_map.get(fact.get("fact_type", "other"), fact.get("fact_type", "其他"))
                content = fact.get("content", "")[:80]
                if len(fact.get("content", "")) > 80:
                    content += "..."
                location = fact.get("location", "-") or _format_location(fact.get("chapter"), fact.get("section"))
                confidence = f"{fact.get('confidence', 1.0) * 100:.0f}%"
                
                cells[0].text = str(idx)
                cells[1].text = type_name
                cells[2].text = content
                cells[3].text = location
                cells[4].text = confidence
        
        # 页脚
        doc.add_paragraph()
        footer = doc.add_paragraph()
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run("报告由 PatPat-Inconsistency-Hunter 自动生成").italic = True
        footer.add_run(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}").italic = True
        
        # 保存到字节流
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()
        
    except ImportError:
        raise ValueError("DOCX生成功能需要安装python-docx库")

