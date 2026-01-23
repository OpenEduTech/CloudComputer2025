import asyncio
import uuid
from datetime import datetime
from typing import Optional
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .agents import LlmAgent
from . import ingestion
from .models import (
    AppealRequest,
    GradeFeedback,
    GradeRequest,
    MaterialCreate,
    MaterialItem,
    MaterialUpdate,
    MemoryCreate,
    MemoryItem,
    MemoryUpdate,
    Quiz,
    QuizRequest,
    QuizSubmission,
    WeaknessBook,
)
from .storage import DataStore

app = FastAPI(title="Learning Evaluation Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
store = DataStore()
agent = LlmAgent()


def get_store() -> DataStore:
    return store


def get_agent() -> LlmAgent:
    return agent


def _parse_tags(raw: Optional[str]) -> Optional[list[str]]:
    if not raw:
        return None
    tags = [tag.strip() for tag in raw.split(",") if tag.strip()]
    return tags or None


async def _create_material(payload: MaterialCreate, store: DataStore, agent: LlmAgent) -> JSONResponse:
    material_id = store.save_material(payload)
    memory_payload: Optional[MemoryCreate] = None
    memory_generated = False
    manual_content = (payload.memory_content or "").strip()
    if manual_content:
        manual_title = (payload.memory_title or payload.topic or "记忆点").strip()
        if not manual_title:
            manual_title = "记忆点"
        memory_payload = MemoryCreate(
            user_id=payload.user_id,
            title=manual_title,
            content=manual_content,
            tags=payload.memory_tags,
        )
    else:
        generated = await agent.generate_memory(payload)
        if generated:
            memory_payload = MemoryCreate(
                user_id=payload.user_id,
                title=generated["title"],
                content=generated["content"],
                tags=generated.get("tags"),
            )
            memory_generated = True

    memory_info = None
    if memory_payload:
        memory_id = store.create_memory(memory_payload)
        memory_info = {"memory_id": memory_id, "title": memory_payload.title}

    return JSONResponse(
        {
            "material_id": material_id,
            "memory_generated": memory_generated,
            "memory_info": memory_info,
        }
    )


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/materials")
async def add_material(
    payload: MaterialCreate,
    store: DataStore = Depends(get_store),
    agent: LlmAgent = Depends(get_agent),
) -> JSONResponse:
    return await _create_material(payload, store, agent)


@app.post("/materials/ingest")
async def ingest_material(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    topic: Optional[str] = Form(None),
    memory_title: Optional[str] = Form(None),
    memory_content: Optional[str] = Form(None),
    memory_tags: Optional[str] = Form(None),
    store: DataStore = Depends(get_store),
    agent: LlmAgent = Depends(get_agent),
) -> JSONResponse:
    raw = await file.read()
    text = ingestion.guess_material_text(file.filename, raw)
    payload = MaterialCreate(
        user_id=user_id,
        topic=topic,
        content=text,
        memory_title=memory_title,
        memory_content=memory_content,
        memory_tags=_parse_tags(memory_tags),
    )
    return await _create_material(payload, store, agent)


@app.get("/materials", response_model=list[MaterialItem])
async def list_materials(
    user_id: str,
    topic: Optional[str] = None,
    keyword: Optional[str] = None,
    store: DataStore = Depends(get_store),
) -> list[MaterialItem]:
    docs = store.list_materials(user_id=user_id, topic=topic, keyword=keyword)
    return [MaterialItem(**d) for d in docs]


@app.patch("/materials/{material_id}")
async def update_material(
    material_id: str,
    payload: MaterialUpdate,
    user_id: str,
    store: DataStore = Depends(get_store),
) -> JSONResponse:
    ok = store.update_material(user_id=user_id, material_id=material_id, payload=payload)
    if not ok:
        raise HTTPException(status_code=404, detail="Material not found or no changes")
    return JSONResponse({"updated": True})


@app.delete("/materials/{material_id}")
async def delete_material(material_id: str, user_id: str, store: DataStore = Depends(get_store)) -> JSONResponse:
    ok = store.delete_material(user_id=user_id, material_id=material_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Material not found")
    return JSONResponse({"deleted": True})


@app.post("/quizzes", response_model=Quiz)
async def create_quiz(
    payload: QuizRequest,
    store: DataStore = Depends(get_store),
    agent: LlmAgent = Depends(get_agent),
) -> Quiz:
    materials = store.list_materials(user_id=payload.user_id, topic=payload.topic, keyword=None)
    if not materials:
        raise HTTPException(status_code=404, detail="No materials found for user/topic")
    quiz = await agent.generate_quiz(materials, payload)
    store.save_quiz(quiz)
    return quiz


@app.post("/grade")
async def grade_quiz(
    payload: GradeRequest,
    store: DataStore = Depends(get_store),
    agent: LlmAgent = Depends(get_agent),
) -> JSONResponse:
    quiz_doc = store.get_quiz(payload.quiz_id)
    if not quiz_doc:
        raise HTTPException(status_code=404, detail="Quiz not found")
    quiz = Quiz.parse_obj(quiz_doc)
    graded = await agent.grade(quiz, payload)
    # persist submission history
    submission_doc = {
        "submission_id": str(uuid.uuid4()),
        "user_id": payload.user_id,
        "quiz_id": payload.quiz_id,
        "answers": [a.dict() for a in payload.answers],
        "feedback": [f.dict() for f in graded.feedback],
        "score": graded.score,
        "created_at": datetime.utcnow().isoformat(),
    }
    store.save_submission(submission_doc)

    for fb in graded.feedback:
        if not fb.correct:
            store.upsert_weakness(
                user_id=payload.user_id,
                entry={
                    "user_id": payload.user_id,
                    "quiz_id": payload.quiz_id,
                    "question_id": fb.question_id,
                    "stem": next((q.stem for q in quiz.questions if q.id == fb.question_id), ""),
                    "last_incorrect_answer": next(
                        (a.answer for a in payload.answers if a.question_id == fb.question_id), ""
                    ),
                    "expected": next((q.answer_key for q in quiz.questions if q.id == fb.question_id), None),
                    "suggested_review": fb.suggested_review,
                    "appeal_status": None,
                },
            )
    return JSONResponse(graded.dict())


@app.get("/weakness-book/{user_id}", response_model=WeaknessBook)
async def weakness_book(user_id: str, store: DataStore = Depends(get_store)) -> WeaknessBook:
    entries = store.list_weaknesses(user_id)
    return WeaknessBook(user_id=user_id, entries=entries)


# Memories CRUD
@app.post("/memories", response_model=MemoryItem)
async def create_memory(payload: MemoryCreate, store: DataStore = Depends(get_store)) -> MemoryItem:
    memory_id = store.create_memory(payload)
    return MemoryItem(memory_id=memory_id, **payload.dict())


@app.get("/memories", response_model=list[MemoryItem])
async def list_memories(user_id: str, keyword: Optional[str] = None, store: DataStore = Depends(get_store)) -> list[MemoryItem]:
    docs = store.list_memories(user_id, keyword)
    return [MemoryItem(**d) for d in docs]


@app.patch("/memories/{memory_id}")
async def update_memory(memory_id: str, payload: MemoryUpdate, user_id: str, store: DataStore = Depends(get_store)) -> JSONResponse:
    ok = store.update_memory(user_id, memory_id, payload)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found or no changes")
    return JSONResponse({"updated": True})


@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, user_id: str, store: DataStore = Depends(get_store)) -> JSONResponse:
    ok = store.delete_memory(user_id, memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return JSONResponse({"deleted": True})


# Quiz history
@app.get("/quizzes/history", response_model=list[QuizSubmission])
async def quiz_history(user_id: str, store: DataStore = Depends(get_store)) -> list[QuizSubmission]:
    docs = store.list_submissions(user_id)
    return [QuizSubmission(**d) for d in docs]


# Appeal wrong answers
@app.post("/weakness-book/appeal")
async def appeal_question(
    payload: AppealRequest,
    store: DataStore = Depends(get_store),
    agent: LlmAgent = Depends(get_agent),
) -> JSONResponse:
    quiz_doc = store.get_quiz(payload.quiz_id)
    if not quiz_doc:
        raise HTTPException(status_code=404, detail="Quiz not found")
    quiz = Quiz.parse_obj(quiz_doc)
    submission = store.get_submission(payload.user_id, payload.quiz_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    answer_item = next((a for a in submission.get("answers", []) if a.get("question_id") == payload.question_id), None)
    feedback_item = next((f for f in submission.get("feedback", []) if f.get("question_id") == payload.question_id), None)
    if not answer_item or not feedback_item:
        raise HTTPException(status_code=404, detail="Question answer not found in submission")
    original_feedback = GradeFeedback(**feedback_item)
    result = await agent.appeal(quiz, payload, answer_item.get("answer", ""), original_feedback)

    if result.correct:
        # remove weakness entry if overturned
        store.remove_weakness(payload.user_id, payload.question_id)
    else:
        store.upsert_weakness(
            user_id=payload.user_id,
            entry={
                "user_id": payload.user_id,
                "question_id": payload.question_id,
                "stem": next((q.stem for q in quiz.questions if q.id == payload.question_id), ""),
                "last_incorrect_answer": answer_item.get("answer", ""),
                "expected": next((q.answer_key for q in quiz.questions if q.id == payload.question_id), None),
                "suggested_review": original_feedback.suggested_review,
                "appeal_status": "rejected",
                "appeal_rationale": result.rationale,
                "appeal_updated_correct": False,
            },
        )

    return JSONResponse(
        {
            "quiz_id": result.quiz_id,
            "question_id": result.question_id,
            "correct": result.correct,
            "rationale": result.rationale,
        }
    )


@app.delete("/weakness-book/{user_id}/{question_id}")
async def delete_weakness_entry(
    user_id: str,
    question_id: str,
    store: DataStore = Depends(get_store),
) -> JSONResponse:
    deleted = store.remove_weakness(user_id, question_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Weakness entry not found")
    return JSONResponse({"deleted": True})
