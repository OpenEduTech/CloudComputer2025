"""
PPT管理API
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import os
import uuid
from datetime import datetime
import logging
import json

from app.core.config import settings
from app.core.database import get_chroma_client, get_redis_client
from app.models.schemas import PPTUploadResponse, PPTParseResponse, StandardResponse
from app.parsers.ppt_parser import PPTParser, DocumentIndexer

logger = logging.getLogger(__name__)
router = APIRouter()


def _ppt_parse_to_markdown(file_id: str, total_slides: int, slides, metadata: dict | None) -> str:
    meta = metadata or {}
    core = meta.get("core_properties") or {}
    doc_title = core.get("title") or f"PPT解析结果：{file_id}"

    lines: list[str] = []
    lines.append(f"# {doc_title}")
    lines.append("")
    lines.append(f"- 文件ID：{file_id}")
    lines.append(f"- 总页数：{total_slides}")
    if core.get("author"):
        lines.append(f"- 作者：{core.get('author')}")
    if core.get("created"):
        lines.append(f"- 创建时间：{core.get('created')}")

    outline_summary = meta.get("outline_summary") or []
    if outline_summary:
        lines.append("")
        lines.append("## 目录概括")
        for s in outline_summary:
            s_text = str(s).strip()
            if s_text:
                lines.append(f"- {s_text}")

    outline = meta.get("outline") or []
    if outline:
        lines.append("")
        lines.append("## 目录结构")
        for o in outline:
            try:
                slide_no = o.get("slide_number")
                title = o.get("title") or "无标题"
                subtitle = o.get("subtitle")
                if subtitle:
                    lines.append(f"- 第 {slide_no} 页：{title} - {subtitle}")
                else:
                    lines.append(f"- 第 {slide_no} 页：{title}")
            except Exception:
                continue

    lines.append("")
    lines.append("---")

    for slide in slides or []:
        try:
            slide_no = getattr(slide, "slide_number", None) or (slide.get("slide_number") if isinstance(slide, dict) else None)
            title = getattr(slide, "title", None) if not isinstance(slide, dict) else slide.get("title")
            subtitle = getattr(slide, "subtitle", None) if not isinstance(slide, dict) else slide.get("subtitle")
            body = getattr(slide, "body", None) if not isinstance(slide, dict) else slide.get("body")
            content = getattr(slide, "content", None) if not isinstance(slide, dict) else slide.get("content")
            image_desc = getattr(slide, "image_descriptions", None) if not isinstance(slide, dict) else slide.get("image_descriptions")
            ocr_texts = getattr(slide, "ocr_texts", None) if not isinstance(slide, dict) else slide.get("ocr_texts")
            notes = getattr(slide, "notes", None) if not isinstance(slide, dict) else slide.get("notes")

            header_title = title or "无标题"
            lines.append("")
            lines.append(f"## 第 {slide_no} 页：{header_title}")
            lines.append("")
            if subtitle:
                lines.append(f"**副标题**：{subtitle}")
                lines.append("")

            main_lines = body if body else content
            main_lines = main_lines or []
            if main_lines:
                lines.append("**正文**：")
                for t in main_lines:
                    t_text = str(t).strip()
                    if t_text:
                        lines.append(f"- {t_text}")
                lines.append("")

            if image_desc:
                cleaned = [str(x).strip() for x in image_desc if str(x).strip()]
                if cleaned:
                    lines.append("**图片描述**：")
                    for d in cleaned:
                        lines.append(f"- {d}")
                    lines.append("")

            if ocr_texts:
                cleaned = [str(x).strip() for x in ocr_texts if str(x).strip()]
                if cleaned:
                    lines.append("**OCR 文本**：")
                    for o in cleaned:
                        lines.append(f"- {o}")
                    lines.append("")

            if notes and str(notes).strip():
                lines.append("**备注**：")
                lines.append(str(notes).strip())
                lines.append("")
        except Exception:
            continue

    return "\n".join(lines).strip() + "\n"


@router.post("/upload", response_model=PPTUploadResponse)
async def upload_ppt(file: UploadFile = File(...), user_id: str = "default"):
    """
    上传PPT文件
    """
    try:
        # 检查文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。允许的类型: {', '.join(settings.allowed_extensions)}"
            )
        
        # 检查文件大小
        contents = await file.read()
        file_size = len(contents)
        if file_size > settings.MAX_UPLOAD_SIZE * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制({settings.MAX_UPLOAD_SIZE}MB)"
            )
        
        # 生成文件ID和保存路径
        file_id = str(uuid.uuid4())
        file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{file_ext}")
        
        # 确保上传目录存在
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # 保存文件
        with open(file_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"文件上传成功: {file_id}, 大小: {file_size} bytes")

        # 记录上传元信息（用于历史与解析关联）
        try:
            redis_client = await get_redis_client()
            upload_meta = {
                "file_id": file_id,
                "filename": file.filename,
                "file_size": file_size,
                "upload_time": str(datetime.now()),
                "user_id": user_id
            }
            await redis_client.set(f"ppt:file:{file_id}", json.dumps(upload_meta, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"记录上传元信息失败: {e}")
        
        return PPTUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=file_size,
            upload_time=datetime.now(),
            message="文件上传成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _index_in_background(file_id: str, slides):
    try:
        chroma_client = get_chroma_client()
        indexer = DocumentIndexer(chroma_client)
        await indexer.index_document(file_id, slides)
        logger.info(f"后台索引完成: {file_id}")
    except Exception as e:
        logger.warning(f"后台索引失败（file_id={file_id}）: {e}")


@router.get("/parse/{file_id}", response_model=PPTParseResponse)
async def parse_ppt(file_id: str, background_tasks: BackgroundTasks, user_id: str = "default"):
    """
    解析PPT文件
    """
    try:
        # 查找文件
        file_path = None
        for ext in settings.allowed_extensions:
            temp_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")
            if os.path.exists(temp_path):
                file_path = temp_path
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 解析文件
        parser = PPTParser(file_path)
        parse_result = await parser.parse()
        
        # 索引到向量数据库（后台执行，避免长时间阻塞请求）
        indexed = False
        try:
            background_tasks.add_task(_index_in_background, file_id, parse_result["slides"])
        except Exception as e:
            logger.warning(f"索引任务提交失败（file_id={file_id}）: {e}")
        
        logger.info(f"文件解析成功: {file_id}")
        
        metadata = dict(parse_result.get("metadata") or {})
        metadata["indexed"] = indexed
        metadata["indexing"] = "background"

        markdown = _ppt_parse_to_markdown(
            file_id=file_id,
            total_slides=parse_result["total_slides"],
            slides=parse_result["slides"],
            metadata=metadata
        )

        # 记录解析历史（简要结构）
        try:
            redis_client = await get_redis_client()
            upload_meta_json = await redis_client.get(f"ppt:file:{file_id}")
            upload_meta = json.loads(upload_meta_json) if upload_meta_json else {}
            history_item = {
                "file_id": file_id,
                "filename": upload_meta.get("filename"),
                "total_slides": parse_result["total_slides"],
                "outline": metadata.get("outline", []),
                "parsed_at": str(datetime.now()),
                "user_id": user_id
            }
            await redis_client.lpush(f"history:ppt:{user_id}", json.dumps(history_item, ensure_ascii=False))
            await redis_client.ltrim(f"history:ppt:{user_id}", 0, 49)
        except Exception as e:
            logger.warning(f"记录解析历史失败: {e}")

        return PPTParseResponse(
            file_id=file_id,
            total_slides=parse_result["total_slides"],
            slides=parse_result["slides"],
            metadata=metadata,
            markdown=markdown
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件解析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}")
async def delete_ppt(file_id: str):
    """
    删除PPT文件
    """
    try:
        # 删除文件
        deleted = False
        for ext in settings.allowed_extensions:
            file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted = True
                break
        
        if not deleted:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        logger.info(f"文件删除成功: {file_id}")
        
        return StandardResponse(
            success=True,
            message="文件删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件删除失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_ppt_history(limit: int = 20, user_id: str = "default"):
    """获取PPT解析历史"""
    try:
        redis_client = await get_redis_client()
        items = await redis_client.lrange(f"history:ppt:{user_id}", 0, max(limit - 1, 0))
        history = []
        for item in items or []:
            try:
                history.append(json.loads(item))
            except Exception:
                continue
        return {"success": True, "items": history}
    except Exception as e:
        logger.error(f"获取解析历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
