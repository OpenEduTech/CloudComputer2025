# 创建 FastAPI app
# 注册所有 router
# 启动服务

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.jobs.queue import queue
from app.api import materials, quizzes, attempts, mistakes, tutor, knowledge, coach

app = FastAPI(title="Learning Evaluation Agent")

origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(materials.router, prefix="/materials")
app.include_router(quizzes.router, prefix="/quizzes")
app.include_router(attempts.router, prefix="/attempts")
app.include_router(mistakes.router, prefix="/mistakes")
app.include_router(coach.router, prefix="/coach")
app.include_router(tutor.router, prefix="/tutor")
app.include_router(knowledge.router, prefix="/knowledge")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/test-job")
async def test_job():
    job = queue.enqueue("worker.hello_job", "Cloud Native")
    return {
        "job_id": job.id,
        "status": "queued"
    }
