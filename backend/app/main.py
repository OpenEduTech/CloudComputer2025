"""
FactGuardian Backend - FastAPI Application
"""
import os
import asyncio
import json
from dotenv import load_dotenv

# Load .env file from root directory before importing services that might use env vars
# Assuming structure: agent/.env and agent/backend/app/main.py
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path)

import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, List
from pydantic import BaseModel
import logging

from app.services.parser import DocumentParser
from app.services.fact_extractor import fact_extractor
from app.services.conflict_detector import conflict_detector
from app.services.verifier import FactVerifier
from app.services.redis_client import redis_client
from app.services.llm_client import llm_client
from app.services.reference_comparator import ReferenceComparator
from app.services.image_extractor import ImageExtractor
from app.services.image_text_comparator import ImageTextComparator
from app.services.progress_manager import progress_manager, ProgressStage

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FactGuardian API",
    description="A cloud-native intelligent agent for long-text fact consistency verification",
    version="1.0.0"
)

# 初始化服务
parser = DocumentParser()
verifier = FactVerifier()
reference_comparator = ReferenceComparator()
image_extractor = ImageExtractor()
image_text_comparator = ImageTextComparator()


@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "message": "FactGuardian API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    redis_status = "connected" if redis_client.is_connected() else "disconnected"
    llm_status = "configured" if llm_client.is_available() else "not_configured"
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "FactGuardian Backend",
            "redis": redis_status,
            "llm": llm_status
        }
    )


@app.get("/api/progress/{document_id}")
async def stream_progress(document_id: str):
    """
    SSE 端点：实时推送分析进度
    
    使用 Server-Sent Events 推送进度更新
    前端可以通过 EventSource 订阅
    """
    async def event_generator():
        queue = progress_manager.subscribe(document_id)
        try:
            while True:
                try:
                    # 等待进度更新，超时10秒发送心跳
                    data = await asyncio.wait_for(queue.get(), timeout=10.0)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    
                    # 如果完成，退出
                    if data.get("stage") == "complete":
                        break
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield f": heartbeat\n\n"
        finally:
            progress_manager.unsubscribe(document_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/progress-status/{document_id}")
async def get_progress_status(document_id: str):
    """
    获取当前进度状态（轮询方式，作为 SSE 的备选）
    """
    progress = progress_manager.get_progress(document_id)
    if not progress:
        return {"exists": False, "message": "进度会话不存在"}
    
    return {
        "exists": True,
        **progress.to_dict()
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档并解析
    
    支持的文件类型：
    - Word 文档 (.docx)
    - PDF 文档 (.pdf)
    - 文本文件 (.txt)
    - Markdown 文件 (.md, .markdown)
    
    返回解析后的结构化文本，包含章节信息
    """
    try:
        # 验证文件类型
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if file_ext not in ['docx', 'pdf', 'txt', 'md', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: docx, pdf, txt, md"
            )
        
        logger.info(f"开始解析文件: {file.filename}, 类型: {file_ext}")
        
        # 读取文件内容
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        # 解析文档
        try:
            result = parser.parse(file_content, file.filename)
        except Exception as e:
            logger.error(f"解析文件失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"文档解析失败: {str(e)}"
            )
        
        # 验证解析结果
        if result['word_count'] == 0:
            raise HTTPException(status_code=400, detail="文档内容为空，无法解析")
        
        logger.info(f"解析成功: {file.filename}, 字数: {result['word_count']}, 章节数: {len(result['sections'])}")
        
        # 生成文档ID
        document_id = str(uuid.uuid4())[:8]

        # 保存解析结果到 Redis，以便后续步骤复用
        document_data = {
            "document_id": document_id,
            "filename": file.filename,
            "file_type": result['file_type'],
            "word_count": result['word_count'],
            "section_count": len(result['sections']),
            "metadata": result['metadata'],
            "sections": result['sections'],
            "text": result['text']
        }
        redis_client.save_document_metadata(document_id, document_data)
        
        # 返回结构化结果
        return {
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "file_type": result['file_type'],
            "word_count": result['word_count'],
            "section_count": len(result['sections']),
            "metadata": result['metadata'],
            "sections": result['sections'],
            "full_text": result['text']  # 完整文本（可选，如果文本很大可以只返回摘要）
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/extract-facts")
async def extract_facts(file: UploadFile = File(...)):
    """
    上传文档并提取事实
    
    流程：
    1. 解析文档
    2. 使用 LLM 提取事实（数据、日期、人名、结论等）
    3. 保存到 Redis
    
    返回提取的事实列表，包含位置信息和置信度
    """
    try:
        # 验证文件类型
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if file_ext not in ['docx', 'pdf', 'txt', 'md', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: docx, pdf, txt, md"
            )
        
        # 检查 LLM 是否可用
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )
        
        logger.info(f"开始处理文件: {file.filename}")
        
        # 读取文件内容
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        # 解析文档
        try:
            parse_result = parser.parse(file_content, file.filename)
        except Exception as e:
            logger.error(f"解析文件失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"文档解析失败: {str(e)}"
            )
        
        if parse_result['word_count'] == 0:
            raise HTTPException(status_code=400, detail="文档内容为空")
        
        # 生成文档ID
        document_id = str(uuid.uuid4())[:8]
        
        # 保存解析结果到 Redis
        document_data = {
            "document_id": document_id,
            "filename": file.filename,
            "file_type": parse_result['file_type'],
            "word_count": parse_result['word_count'],
            "section_count": len(parse_result['sections']),
            "metadata": parse_result['metadata'],
            "sections": parse_result['sections'],
            "text": parse_result['text']
        }
        redis_client.save_document_metadata(document_id, document_data)
        
        logger.info(f"开始提取事实: {file.filename}, 文档ID: {document_id}")
        
        # 提取事实
        try:
            extraction_result = await fact_extractor.extract_from_document(
                document_id=document_id,
                sections=parse_result['sections'],
                filename=file.filename,
                save_to_redis=True
            )
        except Exception as e:
            logger.error(f"事实提取失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"事实提取失败: {str(e)}"
            )
        
        logger.info(f"事实提取完成: {file.filename}, 共 {extraction_result['total_facts']} 条事实")
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "word_count": parse_result['word_count'],
            "section_count": len(parse_result['sections']),
            "total_facts": extraction_result['total_facts'],
            "facts": extraction_result['facts'],
            "statistics": extraction_result['statistics'],
            "section_stats": extraction_result['section_stats'],
            "saved_to_redis": extraction_result.get('saved_to_redis', False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文件时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/documents/{document_id}/extract-facts")
async def extract_facts_by_id(document_id: str):
    """
    根据文档ID提取事实（复用已上传的文档）
    
    前提：必须先调用 /api/upload 上传并解析文档，获取 document_id
    
    进度推送：通过 SSE 端点 /api/progress/{document_id} 获取实时进度
    """
    try:
        # 检查 LLM 是否可用
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )
            
        # 从 Redis 获取文档元数据（包含内容）
        doc_data = redis_client.get_document_metadata(document_id)
        if not doc_data:
            raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 不存在或已过期，请先调用 /api/upload 上传文档"
            )
            
        sections = doc_data.get('sections', [])
        filename = doc_data.get('filename', 'unknown')
        
        if not sections:
            raise HTTPException(
                status_code=400,
                detail="文档内容为空或格式错误"
            )
        
        # 初始化进度会话
        progress_manager.create_session(document_id)
        await progress_manager.update_progress(
            document_id,
            stage=ProgressStage.EXTRACT_FACTS,
            stage_label="提取事实",
            current=0,
            total=len(sections),
            message="准备开始提取事实...",
            sub_message=f"文档: {filename}"
        )
            
        logger.info(f"开始基于ID提取事实: {filename}, 文档ID: {document_id}")
        
        # 提取事实（带进度上报）
        try:
            extraction_result = await fact_extractor.extract_from_document(
                document_id=document_id,
                sections=sections,
                filename=filename,
                save_to_redis=True,
                report_progress=True
            )
        except Exception as e:
            logger.error(f"事实提取失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"事实提取失败: {str(e)}"
            )
            
        logger.info(f"事实提取完成: {filename}, 共 {extraction_result['total_facts']} 条事实")
        
        # 更新进度为完成状态
        await progress_manager.update_progress(
            document_id,
            stage=ProgressStage.EXTRACT_FACTS,
            stage_label="提取事实",
            current=len(sections),
            total=len(sections),
            message=f"事实提取完成！共提取 {extraction_result['total_facts']} 条事实",
            sub_message="",
            mark_stage_complete=True
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": filename,
            "word_count": doc_data.get('word_count', 0),
            "section_count": len(sections),
            "total_facts": extraction_result['total_facts'],
            "facts": extraction_result['facts'],
            "statistics": extraction_result['statistics'],
            "section_stats": extraction_result['section_stats'],
            "saved_to_redis": extraction_result.get('saved_to_redis', False)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取事实时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )



@app.get("/api/facts/{document_id}")
async def get_document_facts(document_id: str):
    """
    获取已保存的文档事实
    
    Args:
        document_id: 文档ID（从 extract-facts 返回）
    
    Returns:
        该文档的所有事实
    """
    try:
        facts = fact_extractor.get_facts(document_id)
        metadata = fact_extractor.get_document_info(document_id)
        
        if facts is None:
            raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 不存在或已过期"
            )
        
        return {
            "success": True,
            "document_id": document_id,
            "metadata": metadata,
            "total_facts": len(facts),
            "facts": facts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取事实失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/detect-conflicts/{document_id}")
async def detect_conflicts(document_id: str):
    """
    检测文档中事实之间的冲突
    
    流程：
    1. 从 Redis 获取已提取的事实
    2. 使用 LLM 成对比对事实
    3. 识别数据不一致、逻辑矛盾、时间冲突等
    4. 保存冲突结果到 Redis
    
    Args:
        document_id: 文档ID（从 extract-facts 返回）
    
    Returns:
        冲突检测结果，包含冲突列表和统计信息
        
    进度推送：通过 SSE 端点 /api/progress/{document_id} 获取实时进度
    """
    try:
        # 检查 LLM 是否可用
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )
        
        # 检查文档是否存在
        facts = fact_extractor.get_facts(document_id)
        if facts is None:
            raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 不存在或已过期，请先使用 /api/extract-facts 提取事实"
            )
        
        # 获取文档元数据（包含章节信息）用于重复检测
        doc_data = redis_client.get_document_metadata(document_id)
        
        sections = doc_data.get('sections', []) if doc_data else []

        logger.info(f"开始冲突检测: 文档 {document_id}, 共 {len(facts)} 条事实")
        
        # 执行冲突检测（带进度上报）
        # 优化策略：
        # - 禁用 LSH（LSH基于文本相似度，会漏掉数值/时间冲突）
        # - 使用结构化字段驱动的智能比对（主体/谓词/数值/时间/极性）
        # - 关键词模式匹配（覆盖典型矛盾场景）
        # - max_pairs=300 保证准确率，速度约15-20秒
        try:
            result = await conflict_detector.detect_conflicts(
                document_id=document_id,
                facts=facts,
                save_to_redis=True,
                use_lsh=False,
                max_pairs=300,
                report_progress=True,
                sections=sections
            )
        except Exception as e:
            logger.error(f"冲突检测失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"冲突检测失败: {str(e)}"
            )
        
        logger.info(f"冲突检测完成: 文档 {document_id}, 发现 {result['conflicts_found']} 个冲突")
        
        # 更新进度为完成状态
        await progress_manager.update_progress(
            document_id,
            stage=ProgressStage.DETECT_CONFLICTS,
            stage_label="冲突检测",
            current=result["total_comparisons"],
            total=result["total_comparisons"],
            message=f"冲突检测完成！发现 {result['conflicts_found']} 个冲突",
            sub_message="",
            mark_stage_complete=True
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "total_facts": result["total_facts"],
            "total_comparisons": result["total_comparisons"],
            "conflicts_found": result["conflicts_found"],
            "conflicts": result["conflicts"],
            "repetitions": result.get("repetitions", []),  # 透传重复内容检测结果
            "statistics": result["statistics"],
            "saved_to_redis": result.get("saved_to_redis", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"冲突检测时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.get("/api/conflicts/{document_id}")
async def get_document_conflicts(document_id: str):
    """
    获取已保存的文档冲突
    
    Args:
        document_id: 文档ID
    
    Returns:
        该文档的所有冲突
    """
    try:
        conflicts = conflict_detector.get_conflicts(document_id)
        
        if conflicts is None:
            raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 的冲突数据不存在，请先使用 /api/detect-conflicts 检测冲突"
            )
        
        return {
            "success": True,
            "document_id": document_id,
            "total_conflicts": len(conflicts),
            "conflicts": conflicts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取冲突失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/documents/{document_id}/verify-facts")
async def verify_facts(document_id: str, only_errors: bool = False):
    """
    溯源校验：对文档提取的事实进行联网验证
    
    Args:
        document_id: 文档ID (必须先调用 /extract-facts)
        only_errors: 是否只返回验证失败的事实（默认 False，返回全部）
        
    Returns:
        验证结果列表，包含每个事实的支持情况、置信度和搜索依据
    """
    try:
        # 检查是否已提取事实
        facts_data = redis_client.get_facts(document_id)
        if not facts_data:
             raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 的事实数据不存在，请先使用 /api/documents/{document_id}/extract-facts 提取事实"
            )
            
        logger.info(f"开始溯源校验: {document_id}")
        
        # 执行校验
        results = await verifier.verify_document_facts(document_id)
        
        # 统计
        supported_count = sum(1 for r in results if r.get('is_supported') and not r.get('skipped', False))
        unsupported_count = sum(1 for r in results if not r.get('is_supported') and not r.get('skipped', False))
        skipped_count = sum(1 for r in results if r.get('skipped', False))
        
        # 如果 only_errors=True，只返回验证失败的
        filtered_results = results
        if only_errors:
            filtered_results = [r for r in results if not r.get('is_supported') and not r.get('skipped', False)]
        
        # 更新进度为完成状态
        await progress_manager.update_progress(
            document_id,
            stage=ProgressStage.VERIFY_FACTS,
            stage_label="溯源校验",
            current=len(results),
            total=len(results),
            message=f"溯源校验完成！已验证 {len(results)} 条事实",
            sub_message=f"支持: {supported_count}, 不支持: {unsupported_count}, 跳过: {skipped_count}",
            mark_stage_complete=True
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "statistics": {
                "total": len(results),
                "supported": supported_count,
                "unsupported": unsupported_count,
                "skipped": skipped_count
            },
            "verified_count": len(filtered_results),
            "verifications": filtered_results,
            "debug": getattr(verifier, "last_debug", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"溯源校验失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    一站式文档分析（上传 -> 提取事实 -> 检测冲突 -> 溯源校验）
    
    流程：
    1. 解析文档
    2. 提取事实
    3. 检测冲突
    4. 溯源校验
    5. 返回完整分析结果
    
    支持的文件类型：docx, pdf, txt, md
    """
    try:
        # 验证文件类型
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if file_ext not in ['docx', 'pdf', 'txt', 'md', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: docx, pdf, txt, md"
            )
        
        # 检查 LLM 是否可用
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )
        
        logger.info(f"开始完整分析: {file.filename}")
        
        # 读取文件内容
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        # 1. 解析文档
        try:
            parse_result = parser.parse(file_content, file.filename)
        except Exception as e:
            logger.error(f"解析文件失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"文档解析失败: {str(e)}"
            )
        
        if parse_result['word_count'] == 0:
            raise HTTPException(status_code=400, detail="文档内容为空")
        
        # 生成文档ID
        document_id = str(uuid.uuid4())[:8]
        
        # 2. 提取事实
        logger.info(f"提取事实中: {file.filename}")
        try:
            extraction_result = await fact_extractor.extract_from_document(
                document_id=document_id,
                sections=parse_result['sections'],
                filename=file.filename,
                save_to_redis=True
            )
        except Exception as e:
            logger.error(f"事实提取失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"事实提取失败: {str(e)}"
            )
        
        # 3. 检测冲突
        logger.info(f"检测冲突中: {file.filename}")
        try:
            conflict_result = await conflict_detector.detect_conflicts(
                document_id=document_id,
                facts=extraction_result['facts'],
                save_to_redis=True,
                sections=parse_result['sections']
            )
        except Exception as e:
            logger.error(f"冲突检测失败: {str(e)}")
            # 冲突检测失败不影响整体结果
            conflict_result = {
                "conflicts_found": 0,
                "conflicts": [],
                "statistics": {},
                "error": str(e)
            }
        
        # 4. 溯源校验
        verification_result = {
            "total": 0,
            "supported": 0,
            "unsupported": 0,
            "skipped": 0,
            "items": []
        }
        
        # 只对包含公开事实的文档进行溯源校验
        public_facts_count = sum(1 for f in extraction_result['facts'] if f.get('verifiable_type') != 'internal')
        
        if public_facts_count > 0 and public_facts_count <= 100:  # 限制在100个以内，避免成本过高
            logger.info(f"开始溯源校验: {file.filename}, 公开事实数: {public_facts_count}")
            try:
                verifications = await verifier.verify_document_facts(document_id)
                
                # 统计验证结果
                supported_count = sum(1 for r in verifications if r.get('is_supported') and not r.get('skipped', False))
                unsupported_count = sum(1 for r in verifications if not r.get('is_supported') and not r.get('skipped', False))
                skipped_count = sum(1 for r in verifications if r.get('skipped', False))
                
                verification_result = {
                    "total": len(verifications),
                    "supported": supported_count,
                    "unsupported": unsupported_count,
                    "skipped": skipped_count,
                    "items": verifications
                }
                logger.info(f"溯源校验完成: 验证 {len(verifications)} 个事实, 通过 {supported_count}, 失败 {unsupported_count}")
            except Exception as e:
                logger.warning(f"溯源校验失败（不影响主流程）: {str(e)}")
                verification_result["error"] = str(e)
        else:
            logger.info(f"跳过溯源校验: 公开事实数={public_facts_count}, 超过阈值或无公开事实")
        
        logger.info(f"分析完成: {file.filename}, 事实: {extraction_result['total_facts']}, 冲突: {conflict_result['conflicts_found']}")
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "word_count": parse_result['word_count'],
            "section_count": len(parse_result['sections']),
            "analysis": {
                "facts": {
                    "total": extraction_result['total_facts'],
                    "items": extraction_result['facts'],
                    "statistics": extraction_result['statistics']
                },
                "conflicts": {
                    "total": conflict_result['conflicts_found'],
                    "items": conflict_result['conflicts'],
                    "statistics": conflict_result.get('statistics', {})
                },
                "verification": verification_result
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析文件时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/upload-multiple")
async def upload_multiple_documents(
    main_doc: UploadFile = File(..., description="主文档"),
    ref_docs: List[UploadFile] = File(..., description="参考文档列表")
):
    """
    上传主文档和多个参考文档
    
    支持的文件类型：docx, pdf, txt, md
    
    Returns:
        - main_document_id: 主文档ID
        - reference_document_ids: 参考文档ID列表
    """
    try:
        # 1. 解析主文档
        main_content = await main_doc.read()
        if len(main_content) == 0:
            raise HTTPException(status_code=400, detail="主文档文件为空")
        
        main_result = parser.parse(main_content, main_doc.filename)
        main_doc_id = str(uuid.uuid4())[:8]
        
        main_doc_data = {
            "document_id": main_doc_id,
            "filename": main_doc.filename,
            "document_type": "main",
            "file_type": main_result['file_type'],
            "word_count": main_result['word_count'],
            "section_count": len(main_result['sections']),
            "metadata": main_result['metadata'],
            "sections": main_result['sections'],
            "text": main_result['text']
        }
        redis_client.save_document_metadata(main_doc_id, main_doc_data)
        
        logger.info(f"主文档上传成功: {main_doc.filename}, ID: {main_doc_id}")
        
        # 2. 解析所有参考文档
        ref_doc_ids = []
        for idx, ref_doc in enumerate(ref_docs):
            ref_content = await ref_doc.read()
            if len(ref_content) == 0:
                logger.warning(f"参考文档 {idx+1} ({ref_doc.filename}) 为空，跳过")
                continue
            
            try:
                ref_result = parser.parse(ref_content, ref_doc.filename)
                ref_doc_id = str(uuid.uuid4())[:8]
                
                ref_doc_data = {
                    "document_id": ref_doc_id,
                    "filename": ref_doc.filename,
                    "document_type": "reference",
                    "file_type": ref_result['file_type'],
                    "word_count": ref_result['word_count'],
                    "section_count": len(ref_result['sections']),
                    "metadata": ref_result['metadata'],
                    "sections": ref_result['sections'],
                    "text": ref_result['text']
                }
                redis_client.save_document_metadata(ref_doc_id, ref_doc_data)
                ref_doc_ids.append(ref_doc_id)
                
                logger.info(f"参考文档 {idx+1} 上传成功: {ref_doc.filename}, ID: {ref_doc_id}")
            except Exception as e:
                logger.error(f"解析参考文档 {ref_doc.filename} 失败: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"参考文档 {ref_doc.filename} 解析失败: {str(e)}"
                )
        
        if not ref_doc_ids:
            raise HTTPException(status_code=400, detail="没有成功解析任何参考文档")
        
        return {
            "success": True,
            "main_document_id": main_doc_id,
            "main_filename": main_doc.filename,
            "reference_document_ids": ref_doc_ids,
            "reference_count": len(ref_doc_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"多文件上传失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


class ReferenceComparisonRequest(BaseModel):
    main_doc_id: str
    ref_doc_ids: List[str]
    similarity_threshold: float = 0.3

@app.post("/api/compare-references")
async def compare_with_reference(request: ReferenceComparisonRequest):
    """
    对比主文档与参考文档的相似度
    
    Args:
        request: 包含主文档ID、参考文档ID列表和相似度阈值的请求体
    
    Returns:
        相似段落列表和统计信息
    """
    main_doc_id = request.main_doc_id
    ref_doc_ids = request.ref_doc_ids
    similarity_threshold = request.similarity_threshold

    try:
        # 检查 LLM 是否可用
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )
        
        # 验证阈值范围
        if not 0 <= similarity_threshold <= 1:
            raise HTTPException(
                status_code=400,
                detail="similarity_threshold 必须在 0-1 之间"
            )
        
        logger.info(f"开始参考对比: 主文档 {main_doc_id} vs {len(ref_doc_ids)} 个参考文档")
        
        result = await reference_comparator.compare_documents(
            main_doc_id=main_doc_id,
            ref_doc_ids=ref_doc_ids,
            similarity_threshold=similarity_threshold
        )
        
        # 保存结果到 Redis（可选）
        comparison_key = f"{main_doc_id}:comparisons"
        redis_client.save_document_metadata(comparison_key, result)
        
        return {
            "success": True,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"参考对比失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"参考对比失败: {str(e)}"
        )


@app.post("/api/extract-from-image")
async def extract_image_content(file: UploadFile = File(...)):
    """
    上传图片并提取内容描述
    
    支持格式: PNG, JPG, JPEG, GIF, WEBP
    
    需要配置 Vision API Key:
    - OPENAI_API_KEY (使用 GPT-4V)
    - 或 ANTHROPIC_API_KEY (使用 Claude Vision)
    """
    try:
        # 验证文件类型
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if file_ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的图片格式: {file_ext}。支持: png, jpg, jpeg, gif, webp"
            )
        
        # 检查服务是否可用
        if not image_extractor.is_available():
            raise HTTPException(
                status_code=503,
                detail="图片提取服务不可用，请配置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY"
            )
        
        # 读取图片内容
        image_content = await file.read()
        
        if len(image_content) == 0:
            raise HTTPException(status_code=400, detail="图片文件为空")
        
        logger.info(f"开始提取图片内容: {file.filename}, 大小: {len(image_content)} bytes")
        
        # 提取内容
        result = await image_extractor.extract_from_image(
            image_content, file.filename
        )
        
        logger.info(f"图片内容提取完成: {file.filename}")
        
        return {
            "success": True,
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片提取失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"图片提取失败: {str(e)}"
        )


@app.post("/api/compare-image-text")
async def compare_image_with_text(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    relevant_sections: Optional[str] = Form(None)
):
    """
    对比图片与文档的一致性
    
    Args:
        file: 图片文件
        document_id: 文档ID（如果提供，将对比文档内容；如果不提供，只提取图片内容）
        relevant_sections: 相关章节索引列表（可选，None 表示所有章节）
    
    Returns:
        如果提供 document_id: 返回对比结果
        如果不提供 document_id: 只返回图片提取结果
    """
    try:
        # 验证图片格式
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if file_ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的图片格式: {file_ext}。支持: png, jpg, jpeg, gif, webp"
            )
        
        # 检查服务是否可用
        if not image_extractor.is_available():
            raise HTTPException(
                status_code=503,
                detail="图片提取服务不可用，请配置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY"
            )
        
        # 读取图片
        image_content = await file.read()
        
        if len(image_content) == 0:
            raise HTTPException(status_code=400, detail="图片文件为空")
        
        if not document_id:
            # 只提取图片内容
            logger.info(f"只提取图片内容: {file.filename}")
            result = await image_extractor.extract_from_image(
                image_content, file.filename
            )
            return {
                "success": True,
                "mode": "extraction_only",
                **result
            }

        # 解析 relevant_sections（从字符串转换为列表）
        parsed_sections = None
        if relevant_sections:
            try:
                parsed_sections = [int(x.strip()) for x in relevant_sections.split(',')]
            except ValueError:
                logger.warning(f"无法解析 relevant_sections: {relevant_sections}")

        # 检查 LLM 是否可用（对比需要 LLM）
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )

        # 对比图片与文档
        logger.info(f"开始图文对比: {file.filename} vs 文档 {document_id}")

        result = await image_text_comparator.compare_image_with_document(
            image_content=image_content,
            image_filename=file.filename,
            document_id=document_id,
            relevant_sections=parsed_sections
        )
        
        logger.info(f"图文对比完成: {file.filename}")
        
        return {
            "success": True,
            "mode": "comparison",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图文对比失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"图文对比失败: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )

