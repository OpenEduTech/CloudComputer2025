"""
API路由定义
定义PPT扩展智能体的所有API端点
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
import uuid
import os
import logging
from pathlib import Path

from services.parser import PPTParser
from services.knowledge_expander import KnowledgeExpander
from services.search_service import SearchService
from services.export_service import export_service
from services.reference_parser import ReferenceParser
from agents.ppt_agent import PPTExtensionAgent

logger = logging.getLogger(__name__)

router = APIRouter()

parser = PPTParser()
expander = KnowledgeExpander()
search_service = SearchService()
reference_parser = ReferenceParser()

# 工作流编排层：把 routes 里分散的步骤收拢到 agent
ppt_agent = PPTExtensionAgent(
    parser=parser,
    expander=expander,
    search_service=search_service,
    reference_parser=reference_parser,
    export_service=export_service,
)

# 参考文件存储（使用内存字典，实际生产环境建议使用Redis）
reference_files_store = {}


class PPTURLRequest(BaseModel):
    """PPT URL请求模型"""
    url: str
    options: Optional[dict] = None


class ExpansionRequest(BaseModel):
    """知识扩充请求模型"""
    content: str
    title: str
    context: Optional[dict] = None
    reference_file_ids: Optional[List[str]] = None  # 参考文件ID列表


class BatchExpansionRequest(BaseModel):
    """批量扩充请求模型"""
    knowledge_points: List[dict]


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str
    sources: Optional[List[str]] = None
    max_results: Optional[int] = 3


class VectorSearchRequest(BaseModel):
    """向量搜索请求模型"""
    query: str
    top_k: Optional[int] = 5
    page_number: Optional[int] = None


@router.post("/upload-reference")
async def upload_reference_file(file: UploadFile = File(...)):
    """
    上传参考文件（Word/PDF）作为PPT扩充的依据
    
    Args:
        file: 上传的参考文件（支持 .docx, .doc, .pdf 格式）
        
    Returns:
        参考文件ID和解析结果
    """
    try:
        logger.info(f"收到参考文件上传请求: {file.filename}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.docx', '.doc', '.pdf']:
            raise HTTPException(status_code=400, detail="仅支持.docx、.doc和.pdf格式的文件")
        
        file_id = str(uuid.uuid4())
        
        upload_dir = Path("./uploads/references")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"参考文件已保存: {file_path}")
        
        # 解析参考文件
        parsed_data = reference_parser.parse_file(str(file_path))
        
        # 存储解析结果
        reference_files_store[file_id] = {
            "file_id": file_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "parsed_data": parsed_data,
            "upload_time": os.path.getmtime(file_path)
        }
        
        logger.info(f"参考文件解析完成: {file_id}, 字数: {parsed_data['word_count']}")
        
        return {
            "message": "参考文件上传成功",
            "file_id": file_id,
            "filename": file.filename,
            "file_type": file_ext,
            "word_count": parsed_data["word_count"],
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"参考文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"参考文件上传失败: {str(e)}")


@router.get("/reference/{file_id}")
async def get_reference_file(file_id: str):
    """
    获取参考文件信息
    
    Args:
        file_id: 参考文件ID
        
    Returns:
        参考文件信息
    """
    if file_id not in reference_files_store:
        raise HTTPException(status_code=404, detail="参考文件不存在")
    
    ref_data = reference_files_store[file_id]
    return {
        "file_id": ref_data["file_id"],
        "filename": ref_data["filename"],
        "word_count": ref_data["parsed_data"]["word_count"],
        "file_type": ref_data["parsed_data"]["file_type"]
    }


@router.delete("/reference/{file_id}")
async def delete_reference_file(file_id: str):
    """
    删除参考文件
    
    Args:
        file_id: 参考文件ID
        
    Returns:
        删除结果
    """
    if file_id not in reference_files_store:
        raise HTTPException(status_code=404, detail="参考文件不存在")
    
    ref_data = reference_files_store[file_id]
    file_path = Path(ref_data["file_path"])
    
    # 删除文件
    if file_path.exists():
        file_path.unlink()
    
    # 从存储中删除
    del reference_files_store[file_id]
    
    return {"message": "参考文件已删除", "file_id": file_id}


@router.post("/upload")
async def upload_ppt(file: UploadFile = File(...)):
    """
    上传PPT文件并开始处理
    
    Args:
        file: 上传的PPT文件（支持 .pptx, .ppt 格式）
        
    Returns:
        处理任务ID和状态
    """
    try:
        logger.info(f"收到文件上传请求: {file.filename}")
        
        if not file.filename.endswith(('.pptx', '.ppt')):
            raise HTTPException(status_code=400, detail="仅支持.pptx和.ppt格式的文件")
        
        task_id = str(uuid.uuid4())
        
        upload_dir = Path("./uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / f"{task_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"文件已保存: {file_path}")
        
        ppt_data = parser.parse_from_file(str(file_path))
        
        chunks = parser.extract_text_chunks(ppt_data)
        
        try:
            from utils.vector_db import VectorDB
            vector_db = VectorDB()
            vector_db.insert_chunks(chunks)
            logger.info(f"已向量化{len(chunks)}个文本切片")
        except Exception as e:
            logger.warning(f"向量化失败（可能Milvus未启动）: {str(e)}")
        
        return {
            "message": "文件上传成功",
            "task_id": task_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "completed",
            "ppt_data": {
                "metadata": ppt_data.get("metadata"),
                "slide_count": len(ppt_data.get("slides", [])),
                "slides": ppt_data.get("slides", [])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/process-url")
async def process_ppt_url(request: PPTURLRequest):
    """
    从URL处理PPT文件
    
    Args:
        request: 包含PPT URL的请求体
        
    Returns:
        处理任务ID和状态
        
    Example:
        {
            "url": "https://example.com/presentation.pptx",
            "options": {}
        }
    """
    try:
        logger.info(f"收到URL处理请求: {request.url}")
        
        task_id = str(uuid.uuid4())
        
        ppt_data = parser.parse_from_url(request.url)
        
        chunks = parser.extract_text_chunks(ppt_data)
        
        try:
            from utils.vector_db import VectorDB
            vector_db = VectorDB()
            vector_db.insert_chunks(chunks)
            logger.info(f"已向量化{len(chunks)}个文本切片")
        except Exception as e:
            logger.warning(f"向量化失败（可能Milvus未启动）: {str(e)}")
        
        return {
            "message": "URL处理成功",
            "task_id": task_id,
            "url": request.url,
            "status": "completed",
            "ppt_data": {
                "metadata": ppt_data.get("metadata"),
                "slide_count": len(ppt_data.get("slides", [])),
                "slides": ppt_data.get("slides", [])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"URL处理失败: {str(e)}")


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    查询处理任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态和结果（如果完成）
    """
    return {
        "task_id": task_id,
        "status": "completed",
        "message": "任务已完成"
    }


@router.post("/expand")
async def expand_knowledge(request: ExpansionRequest):
    """
    扩充单个知识点
    
    Args:
        request: 扩充请求，包含内容和上下文
        
    Returns:
        扩充后的内容
        
    Example:
        {
            "title": "机器学习基础",
            "content": "监督学习",
            "context": {"chapter": "第一章"},
            "reference_file_ids": ["file_id_1", "file_id_2"]
        }
    """
    try:
        logger.info(f"收到知识扩充请求: {request.title}")
        return ppt_agent.run_expand_workflow(
            title=request.title,
            content=request.content,
            context=request.context,
            reference_file_ids=request.reference_file_ids,
            reference_files_store=reference_files_store,
            validate=False,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # 容错：即使异常也返回可展示结构，避免前端“空白/崩溃”
        logger.error(f"知识扩充失败(兜底返回): {str(e)}")
        return {
            "title": request.title,
            "original_content": request.content,
            "expanded_content": {
                "background": "",
                "principles": "",
                "formulas": "",
                "examples": "",
                "summary": "出错啦，请重新上传或稍后重试。",
                "references": [],
            },
            "reference_files_used": [],
            "status": "failed",
            "attempts": 0,
        }


@router.post("/expand-with-validation")
async def expand_with_validation(request: ExpansionRequest):
    """
    带验证的知识扩充
    
    Args:
        request: 扩充请求
        
    Returns:
        扩充后的内容和验证结果
    """
    try:
        logger.info(f"收到带验证的知识扩充请求: {request.title}")
        return ppt_agent.run_expand_workflow(
            title=request.title,
            content=request.content,
            context=request.context,
            reference_file_ids=request.reference_file_ids,
            reference_files_store=reference_files_store,
            validate=True,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"知识扩充失败(兜底返回): {str(e)}")
        return {
            "title": request.title,
            "original_content": request.content,
            "expanded_content": {
                "background": "",
                "principles": "",
                "formulas": "",
                "examples": "",
                "summary": "出错啦，请重新上传或稍后重试。",
                "references": [],
            },
            "validation": {
                "is_relevant": False,
                "is_accurate": False,
                "is_consistent": False,
                "confidence": 0.0,
                "issues": [f"服务异常: {str(e)}"],
            },
            "reference_files_used": [],
            "status": "failed",
            "attempts": 0,
        }


@router.post("/batch-expand")
async def batch_expand_knowledge(request: BatchExpansionRequest):
    """
    批量扩充知识点
    
    Args:
        request: 批量扩充请求
        
    Returns:
        扩充后的知识点列表
    """
    try:
        logger.info(f"收到批量扩充请求，共{len(request.knowledge_points)}个知识点")
        return ppt_agent.run_batch_expand_workflow(request.knowledge_points)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量扩充失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量扩充失败: {str(e)}")


@router.post("/search")
async def search_knowledge(request: SearchRequest):
    """
    多源搜索知识
    
    Args:
        request: 搜索请求
        
    Returns:
        搜索结果
    """
    try:
        logger.info(f"收到搜索请求: {request.query}")
        
        results = search_service.multi_source_search(
            query=request.query,
            sources=request.sources,
            max_results_per_source=request.max_results
        )
        
        total_results = sum(len(r) for r in results.values())
        
        return {
            "query": request.query,
            "total_results": total_results,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/vector-search")
async def vector_search(request: VectorSearchRequest):
    """
    向量语义搜索
    
    Args:
        request: 向量搜索请求
        
    Returns:
        语义搜索结果
    """
    try:
        logger.info(f"收到向量搜索请求: {request.query}")
        
        from utils.vector_db import VectorDB
        vector_db = VectorDB()
        results = vector_db.search(
            query=request.query,
            top_k=request.top_k,
            page_number=request.page_number
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"向量搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"向量搜索失败: {str(e)}")


@router.get("/vector-db/stats")
async def get_vector_db_stats():
    """
    获取向量数据库统计信息
    
    Returns:
        统计信息
    """
    try:
        from utils.vector_db import VectorDB
        vector_db = VectorDB()
        stats = vector_db.get_collection_stats()
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.delete("/vector-db")
async def clear_vector_db():
    """
    清空向量数据库
    
    Returns:
        操作结果
    """
    try:
        from utils.vector_db import VectorDB
        vector_db = VectorDB()
        vector_db.delete_all()
        return {"message": "向量数据库已清空"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空向量数据库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空向量数据库失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "ppt-extension-agent",
        "version": "0.1.0"
    }


class ExportRequest(BaseModel):
    """导出请求模型"""
    ppt_data: dict
    expanded_data: dict
    format: str = "markdown"
    page_number: Optional[int] = None


@router.post("/export")
async def export_content(request: ExportRequest):
    """
    导出扩展内容
    
    Args:
        request: 导出请求，包含PPT数据、扩展数据和格式
        
    Returns:
        导出文件的下载链接或内容
    """
    try:
        logger.info(f"收到导出请求，格式: {request.format}")
        
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)
        
        if request.format.lower() == "markdown":
            markdown_content = export_service.export_to_markdown(
                request.ppt_data,
                request.expanded_data,
                request.page_number
            )
            
            filename = f"export_{uuid.uuid4().hex[:8]}.md"
            file_path = output_dir / filename
            
            export_service.save_markdown(markdown_content, str(file_path))
            
            return {
                "status": "success",
                "format": "markdown",
                "filename": filename,
                "content": markdown_content,
                "download_url": f"/api/v1/download/{filename}"
            }
        
        elif request.format.lower() == "pdf":
            markdown_content = export_service.export_to_markdown(
                request.ppt_data,
                request.expanded_data,
                request.page_number
            )
            
            filename = f"export_{uuid.uuid4().hex[:8]}.pdf"
            file_path = output_dir / filename
            
            export_service.export_to_pdf(markdown_content, str(file_path))
            
            return {
                "status": "success",
                "format": "pdf",
                "filename": filename,
                "download_url": f"/api/v1/download/{filename}"
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"不支持的导出格式: {request.format}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    下载导出的文件
    
    Args:
        filename: 文件名
        
    Returns:
        文件内容
    """
    try:
        from fastapi.responses import FileResponse
        
        file_path = Path("./output") / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")
