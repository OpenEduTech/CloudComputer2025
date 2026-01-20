from fastapi import FastAPI

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
