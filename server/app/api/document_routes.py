"""
PatPat-Inconsistency-Hunter 用户文档API路由
管理用户的个人文档、图片上传、格式转换等
"""

import uuid
import os
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import User, UserDocument, DocumentImage, Document, AnalysisHistory
from ..services.document_editor import (
    get_document_editor, 
    RichTextContent,
    ALLOWED_IMAGE_TYPES,
    MAX_IMAGE_SIZE,
)
from ..utils.logger import logger
from ..utils.db_session import get_db_session, async_session_maker
from .auth_routes import get_current_user


router = APIRouter(prefix="/documents", tags=["用户文档"])


# ==================== 请求/响应模型 ====================

class CreateDocumentRequest(BaseModel):
    """创建文档请求"""
    title: str = Field(..., min_length=1, max_length=256)
    content: str = Field(default="")
    content_json: dict = Field(default_factory=dict)


class UpdateDocumentRequest(BaseModel):
    """更新文档请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[dict] = None


class DocumentResponse(BaseModel):
    """文档响应"""
    document_id: str
    title: str
    content: str
    content_json: dict
    content_html: str
    word_count: int
    status: str
    version: int
    last_analysis_task_id: Optional[str]
    last_analysis_at: Optional[str]
    analysis_count: int
    created_at: str
    updated_at: str


class DocumentListItem(BaseModel):
    """文档列表项"""
    document_id: str
    title: str
    word_count: int
    status: str
    analysis_count: int
    last_analysis_at: Optional[str]
    created_at: str
    updated_at: str


class ImageUploadResponse(BaseModel):
    """图片上传响应"""
    image_id: str
    file_name: str
    file_url: str
    file_size: int
    width: Optional[int]
    height: Optional[int]


class ExportRequest(BaseModel):
    """导出请求"""
    format: str = Field(..., description="导出格式: markdown/html/pdf")


# ==================== API 端点 ====================

@router.get("", response_model=List[DocumentListItem])
async def list_documents(
    status: Optional[str] = Query(None, description="文档状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户的文档列表
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    
    async with async_session_maker() as db:
        query = select(UserDocument).where(UserDocument.user_id == current_user.id)
        
        if status:
            query = query.where(UserDocument.status == status)
        
        query = query.order_by(desc(UserDocument.updated_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return [
            DocumentListItem(
                document_id=doc.document_id,
                title=doc.title,
                word_count=doc.word_count,
                status=doc.status,
                analysis_count=doc.analysis_count,
                last_analysis_at=doc.last_analysis_at.isoformat() if doc.last_analysis_at else None,
                created_at=doc.created_at.isoformat(),
                updated_at=doc.updated_at.isoformat(),
            )
            for doc in documents
        ]


@router.post("", response_model=DocumentResponse)
async def create_document(
    request: CreateDocumentRequest,
    current_user: User = Depends(get_current_user),
):
    """
    创建新文档
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # 如果没有富文本内容，从纯文本生成
    content_json = request.content_json
    if not content_json and request.content:
        content_json = RichTextContent.from_plain_text(request.content)
    elif not content_json:
        content_json = RichTextContent.create_empty()
    
    # 生成HTML和统计字数
    content_html = RichTextContent.to_html(content_json)
    word_count = RichTextContent.word_count(content_json)
    
    async with async_session_maker() as db:
        doc = UserDocument(
            document_id=document_id,
            user_id=current_user.id,
            title=request.title,
            content=request.content or RichTextContent.to_plain_text(content_json),
            content_json=content_json,
            content_html=content_html,
            word_count=word_count,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        logger.info(f"创建文档: {document_id}, 用户: {current_user.username}")
        
        return DocumentResponse(
            document_id=doc.document_id,
            title=doc.title,
            content=doc.content,
            content_json=doc.content_json,
            content_html=doc.content_html,
            word_count=doc.word_count,
            status=doc.status,
            version=doc.version,
            last_analysis_task_id=doc.last_analysis_task_id,
            last_analysis_at=doc.last_analysis_at.isoformat() if doc.last_analysis_at else None,
            analysis_count=doc.analysis_count,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    获取文档详情
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    
    async with async_session_maker() as db:
        result = await db.execute(
            select(UserDocument)
            .where(UserDocument.document_id == document_id)
            .where(UserDocument.user_id == current_user.id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return DocumentResponse(
            document_id=doc.document_id,
            title=doc.title,
            content=doc.content,
            content_json=doc.content_json or {},
            content_html=doc.content_html or "",
            word_count=doc.word_count,
            status=doc.status,
            version=doc.version,
            last_analysis_task_id=doc.last_analysis_task_id,
            last_analysis_at=doc.last_analysis_at.isoformat() if doc.last_analysis_at else None,
            analysis_count=doc.analysis_count,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    request: UpdateDocumentRequest,
    current_user: User = Depends(get_current_user),
):
    """
    更新文档
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    
    async with async_session_maker() as db:
        result = await db.execute(
            select(UserDocument)
            .where(UserDocument.document_id == document_id)
            .where(UserDocument.user_id == current_user.id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        if request.title is not None:
            doc.title = request.title
        
        if request.content_json is not None:
            doc.content_json = request.content_json
            doc.content = RichTextContent.to_plain_text(request.content_json)
            doc.content_html = RichTextContent.to_html(request.content_json)
            doc.word_count = RichTextContent.word_count(request.content_json)
        elif request.content is not None:
            doc.content = request.content
            doc.content_json = RichTextContent.from_plain_text(request.content)
            doc.content_html = RichTextContent.to_html(doc.content_json)
            doc.word_count = RichTextContent.word_count(doc.content_json)
        
        doc.version += 1
        doc.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(doc)
        
        logger.info(f"更新文档: {document_id}")
        
        return DocumentResponse(
            document_id=doc.document_id,
            title=doc.title,
            content=doc.content,
            content_json=doc.content_json or {},
            content_html=doc.content_html or "",
            word_count=doc.word_count,
            status=doc.status,
            version=doc.version,
            last_analysis_task_id=doc.last_analysis_task_id,
            last_analysis_at=doc.last_analysis_at.isoformat() if doc.last_analysis_at else None,
            analysis_count=doc.analysis_count,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    删除文档
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    
    async with async_session_maker() as db:
        result = await db.execute(
            select(UserDocument)
            .where(UserDocument.document_id == document_id)
            .where(UserDocument.user_id == current_user.id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        await db.delete(doc)
        await db.commit()
        
        logger.info(f"删除文档: {document_id}")
        
        return {"message": "文档已删除"}


# ==================== 图片上传 ====================

@router.post("/images/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    room_id: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    上传图片
    """
    # 验证文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的图片类型: {file.content_type}")
    
    # 读取文件内容
    content = await file.read()
    
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail=f"图片大小超过限制: {MAX_IMAGE_SIZE / 1024 / 1024}MB")
    
    editor = get_document_editor()
    
    try:
        # 获取文档数据库ID（如果有）
        doc_db_id = None
        if document_id:
            async with async_session_maker() as db:
                result = await db.execute(
                    select(UserDocument).where(UserDocument.document_id == document_id)
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc_db_id = doc.id
        
        # 上传图片
        image_info = await editor.upload_image(
            file_content=content,
            file_name=file.filename,
            mime_type=file.content_type,
            user_id=current_user.id,
            document_id=doc_db_id,
            room_id=room_id,
        )
        
        # 保存到数据库
        async with async_session_maker() as db:
            img = DocumentImage(
                image_id=image_info["image_id"],
                document_id=doc_db_id,
                user_id=current_user.id,
                room_id=room_id,
                file_name=image_info["file_name"],
                file_path=image_info["file_path"],
                file_url=image_info["file_url"],
                file_size=image_info["file_size"],
                mime_type=image_info["mime_type"],
                width=image_info.get("width"),
                height=image_info.get("height"),
            )
            db.add(img)
            await db.commit()
        
        return ImageUploadResponse(
            image_id=image_info["image_id"],
            file_name=image_info["file_name"],
            file_url=image_info["file_url"],
            file_size=image_info["file_size"],
            width=image_info.get("width"),
            height=image_info.get("height"),
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"图片上传失败: {e}")
        raise HTTPException(status_code=500, detail="图片上传失败")


# ==================== 文档导出 ====================

@router.get("/{document_id}/export")
async def export_document(
    document_id: str,
    format: str = Query(..., description="导出格式: markdown/html/pdf"),
    current_user: User = Depends(get_current_user),
):
    """
    导出文档
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    
    async with async_session_maker() as db:
        result = await db.execute(
            select(UserDocument)
            .where(UserDocument.document_id == document_id)
            .where(UserDocument.user_id == current_user.id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        editor = get_document_editor()
        
        if format == "markdown":
            content = editor.convert_to_markdown(doc.content_json or {})
            return Response(
                content=content,
                media_type="text/markdown",
                headers={"Content-Disposition": f'attachment; filename="{doc.title}.md"'}
            )
        
        elif format == "html":
            content = doc.content_html or RichTextContent.to_html(doc.content_json or {})
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{doc.title}</title>
    <style>
        body {{ font-family: "Microsoft YaHei", Arial, sans-serif; line-height: 1.6; padding: 40px; max-width: 800px; margin: 0 auto; }}
    </style>
</head>
<body>
    <h1>{doc.title}</h1>
    {content}
</body>
</html>"""
            return Response(
                content=full_html,
                media_type="text/html",
                headers={"Content-Disposition": f'attachment; filename="{doc.title}.html"'}
            )
        
        elif format == "pdf":
            try:
                pdf_content = await editor.convert_to_pdf(doc.content_json or {}, doc.title)
                return Response(
                    content=pdf_content,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{doc.title}.pdf"'}
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        elif format == "docx":
            try:
                docx_content = await editor.convert_to_docx(doc.content_json or {}, doc.title)
                return Response(
                    content=docx_content,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{doc.title}.docx"'}
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        elif format == "txt":
            content = RichTextContent.to_plain_text(doc.content_json or {}, include_image_placeholders=True)
            return Response(
                content=content,
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{doc.title}.txt"'}
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format}，支持的格式有: markdown, html, pdf, docx, txt")


# ==================== 分析历史 ====================

@router.get("/analysis/history")
async def get_analysis_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户的分析历史
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    
    async with async_session_maker() as db:
        # 查询用户的所有分析记录
        result = await db.execute(
            select(Document)
            .where(cast(Document.doc_metadata["user_id"], String) == current_user.user_id)
            .order_by(desc(Document.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        documents = result.scalars().all()
        
        # 统计总数
        count_result = await db.execute(
            select(func.count(Document.id))
            .where(cast(Document.doc_metadata["user_id"], String) == current_user.user_id)
        )
        total = count_result.scalar() or 0
        
        return {
            "items": [
                {
                    "task_id": doc.task_id,
                    "title": doc.title,
                    "content_length": doc.content_length,
                    "total_facts": doc.total_facts,
                    "total_conflicts": doc.total_conflicts,
                    "analysis_time": doc.analysis_time,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat(),
                    "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
                }
                for doc in documents
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


# ==================== 用户统计 ====================

@router.get("/stats/overview")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
):
    """
    获取用户统计数据
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    
    async with async_session_maker() as db:
        # 文档数量
        doc_count_result = await db.execute(
            select(func.count(UserDocument.id))
            .where(UserDocument.user_id == current_user.id)
        )
        doc_count = doc_count_result.scalar() or 0
        
        # 分析次数
        analysis_count_result = await db.execute(
            select(func.count(Document.id))
            .where(cast(Document.doc_metadata["user_id"], String) == current_user.user_id)
        )
        analysis_count = analysis_count_result.scalar() or 0
        
        # 发现冲突数
        conflict_count_result = await db.execute(
            select(func.sum(Document.total_conflicts))
            .where(cast(Document.doc_metadata["user_id"], String) == current_user.user_id)
        )
        conflict_count = conflict_count_result.scalar() or 0
        
        # 参与的协作房间数
        from ..models.database import RoomMembership
        room_count_result = await db.execute(
            select(func.count(RoomMembership.id))
            .where(RoomMembership.user_id == current_user.id)
        )
        room_count = room_count_result.scalar() or 0
        
        return {
            "document_count": doc_count,
            "analysis_count": analysis_count,
            "conflict_count": int(conflict_count) if conflict_count else 0,
            "collaboration_count": room_count,
        }

