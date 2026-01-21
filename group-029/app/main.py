from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from uuid import uuid4

from app.models import (
    SessionCreateResponse,
    SessionListResponse,
    SessionDeleteResponse,
    SessionRenameRequest,
    SessionRenameResponse,
    SessionTextCreateRequest,
    QuestionGenerateRequest,
    QuestionGenerateResponse,
    QuestionItem,
    GradeRequest,
    GradeResponse,
    GradeItem,
    RecordResponse,
    WrongbookResponse,
    WrongbookDeleteResponse,
)
from app.services.pdf_loader import load_pdf_text
from app.services.text_chunker import split_text
from app.services.session_store import (
    create_session,
    load_chunks,
    list_sessions,
    delete_session,
    update_session_name,
    touch_session,
)
from app.services.session_namer import generate_session_name
from app.services.question_generator import generate_questions
from app.services.grader import grade_answers
from app.services.retriever import select_chunks_for_generation, select_chunks_for_question
from app.services.wrongbook_store import (
    save_wrong_items,
    load_wrong_items_all,
    summarize_wrong_items,
    delete_wrong_item,
)
from app.services.qa_store import save_questions, save_answers, save_grade, load_latest_record

from app.core.config import settings


# API 入口文件：提供健康检查与业务路由
app = FastAPI(title="学习评估与巩固智能体", version="0.1.0")

# 挂载静态前端页面
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health_check():
    # 基础健康检查，返回当前模型配置
    return {
        "status": "ok",
        "model": settings.llm_model,
        "use_langgraph": settings.use_langgraph,
    }


@app.get("/")
def index():
    # 单页前端入口
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/wrongbook")
def wrongbook_page():
    # 错题本独立页面
    return FileResponse(os.path.join(STATIC_DIR, "wrongbook.html"))


@app.post("/sessions", response_model=SessionCreateResponse)
def create_session_api(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    # 确保上传临时目录存在，避免文件名带中文导致路径问题
    os.makedirs("data", exist_ok=True)
    temp_path = os.path.join("data", f"{uuid4().hex}.pdf")
    try:
        content = file.file.read()
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"PDF 超过大小限制（{settings.max_upload_mb}MB）",
            )
        if not content.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="文件不是有效的 PDF")
        with open(temp_path, "wb") as f:
            f.write(content)
        text = load_pdf_text(temp_path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 解析失败: {exc}") from exc

    if not text.strip():
        raise HTTPException(status_code=400, detail="PDF 解析失败或内容为空")

    chunks = split_text(text)
    filename = os.path.splitext(os.path.basename(file.filename))[0]
    session_name = generate_session_name(text, filename)
    session_id = create_session(chunks, session_name)
    return SessionCreateResponse(
        session_id=session_id,
        chunk_count=len(chunks),
        name=session_name,
        source_type="pdf",
    )


@app.post("/sessions/text", response_model=SessionCreateResponse)
def create_session_text_api(req: SessionTextCreateRequest):
    raw_text = (req.text or "").strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="文本内容不能为空")
    chunks = split_text(raw_text)
    session_name = req.name or generate_session_name(raw_text, "文本会话")
    session_id = create_session(chunks, session_name)
    return SessionCreateResponse(
        session_id=session_id,
        chunk_count=len(chunks),
        name=session_name,
        source_type="text",
    )


@app.get("/sessions", response_model=SessionListResponse)
def list_sessions_api():
    return SessionListResponse(sessions=list_sessions())


@app.delete("/sessions/{session_id}", response_model=SessionDeleteResponse)
def delete_session_api(session_id: str):
    deleted = delete_session(session_id)
    return SessionDeleteResponse(session_id=session_id, deleted=deleted)


@app.patch("/sessions/{session_id}", response_model=SessionRenameResponse)
def rename_session_api(session_id: str, req: SessionRenameRequest):
    updated = update_session_name(session_id, req.name)
    return SessionRenameResponse(session_id=session_id, name=req.name, updated=updated)


@app.post("/questions", response_model=QuestionGenerateResponse)
def generate_questions_api(req: QuestionGenerateRequest):
    chunks = load_chunks(req.session_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="未找到会话或切分内容为空")

    # 检索增强：挑选更相关的片段作为上下文
    use_chunks = select_chunks_for_generation(chunks, top_k=10)
    data, raw = generate_questions(use_chunks, req.num_mcq, req.num_short, req.difficulty_ratio)

    # 校验：题目必须包含证据片段
    if data:
        data = [q for q in data if q.get("evidence")]
    if not data:
        raise HTTPException(
            status_code=500,
            detail="题目生成失败，请检查 LLM 配置或 data/llm_raw.txt",
        )

    questions = [QuestionItem(**q) for q in data]
    try:
        save_questions(req.session_id, [q.model_dump() for q in questions])
    except Exception:
        pass
    touch_session(req.session_id)

    return QuestionGenerateResponse(session_id=req.session_id, questions=questions)


@app.post("/grade", response_model=GradeResponse)
def grade_api(req: GradeRequest):
    chunks = load_chunks(req.session_id)
    contexts = []
    for q in req.questions:
        picked = select_chunks_for_question(chunks, q.question, q.answer, top_k=3)
        context_text = "\n".join([f"[{c['chunk_id']}]{c['text']}" for c in picked])
        contexts.append({"qid": q.qid, "context": context_text})
    result, raw = grade_answers(
        [q.model_dump() for q in req.questions],
        req.answers,
        contexts,
    )

    # 校验：结果必须包含解释
    if result:
        result = [r for r in result if r.get("explanation")]
    if not result:
        raise HTTPException(
            status_code=500,
            detail="判卷失败，请检查 LLM 配置或 data/llm_grade_raw.txt",
        )

    items = [GradeItem(**r) for r in result]
    try:
        save_answers(req.session_id, req.answers)
        save_grade(
            req.session_id,
            {
                "total_score": sum(i.score for i in items),
                "items": [i.model_dump() for i in items],
            },
        )
    except Exception:
        pass

    # 收集错题并写入 Redis
    wrong_items = []
    for q in req.questions:
        for r in items:
            if q.qid == r.qid and not r.is_correct:
                wrong_items.append(
                    {
                        "qid": q.qid,
                        "question": q.question,
                        "user_answer": next(
                            (a["answer"] for a in req.answers if a["qid"] == q.qid),
                            "",
                        ),
                        "correct_answer": q.answer,
                        "explanation": r.explanation,
                    }
                )
    try:
        save_wrong_items(req.session_id, wrong_items)
    except Exception:
        # Redis 不可用时不影响判卷结果
        pass

    total_score = sum(i.score for i in items)
    touch_session(req.session_id)
    return GradeResponse(
        session_id=req.session_id,
        total_score=total_score,
        items=items,
    )


@app.get("/wrongbook/all", response_model=WrongbookResponse)
def wrongbook_api_all():
    items = load_wrong_items_all()
    summary = summarize_wrong_items(items)
    return WrongbookResponse(
        session_id="all",
        total_wrong=len(items),
        items=items,
        summary=summary,
    )


@app.delete("/wrongbook/{record_id}", response_model=WrongbookDeleteResponse)
def wrongbook_delete_api(record_id: str):
    deleted = delete_wrong_item(record_id)
    return WrongbookDeleteResponse(record_id=record_id, deleted=deleted)


@app.get("/records/{session_id}", response_model=RecordResponse)
def record_api(session_id: str):
    touch_session(session_id)
    return RecordResponse(**load_latest_record(session_id))
