from fastapi import FastAPI, UploadFile, File, HTTPException
import os
from uuid import uuid4

from app.models import (
    SessionCreateResponse,
    QuestionGenerateRequest,
    QuestionGenerateResponse,
    QuestionItem,
)
from app.services.pdf_loader import load_pdf_text
from app.services.text_chunker import split_text
from app.services.session_store import create_session, load_chunks
from app.services.question_generator import generate_questions

from app.core.config import settings


# API 入口文件：提供健康检查与后续业务路由
app = FastAPI(title="学习评估与巩固智能体", version="0.1.0")


@app.get("/health")
def health_check():
    # 基础健康检查，返回当前模型配置
    return {
        "status": "ok",
        "model": settings.llm_model,
        "use_langgraph": settings.use_langgraph,
    }


@app.post("/sessions", response_model=SessionCreateResponse)
def create_session_api(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")
    # 确保上传临时目录存在，避免文件名带中文导致路径问题
    os.makedirs("data", exist_ok=True)
    temp_path = os.path.join("data", f"{uuid4().hex}.pdf")
    try:
        with open(temp_path, "wb") as f:
            f.write(file.file.read())
        text = load_pdf_text(temp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 解析失败: {exc}") from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="PDF 解析失败或内容为空")
    chunks = split_text(text)
    session_id = create_session(chunks)
    return SessionCreateResponse(session_id=session_id, chunk_count=len(chunks))


@app.post("/questions", response_model=QuestionGenerateResponse)
def generate_questions_api(req: QuestionGenerateRequest):
    chunks = load_chunks(req.session_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="未找到会话或切分内容为空")
    # 简化策略：取前若干片段作为上下文
    use_chunks = chunks[:10]
    data, raw = generate_questions(use_chunks, req.num_mcq, req.num_short)
    if not data:
        raise HTTPException(
            status_code=500,
            detail="题目生成失败，请检查 LLM 配置或 data/llm_raw.txt",
        )
    questions = [QuestionItem(**q) for q in data]
    return QuestionGenerateResponse(session_id=req.session_id, questions=questions)
