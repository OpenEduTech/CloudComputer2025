"""
FastAPI主应用入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api import ppt, knowledge, questions, mistakes
from app.core.database import init_db, close_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("应用启动中...")
    await init_db()
    logger.info("数据库初始化完成")
    
    yield
    
    # 关闭时清理
    logger.info("应用关闭中...")
    await close_db()
    logger.info("资源清理完成")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="基于云原生和LLM Agents的PPT智能学习助手",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "1.0.0"
    }


# 根路由
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用PPT学习助手API",
        "docs": "/docs",
        "health": "/health"
    }


# 注册路由
app.include_router(ppt.router, prefix="/api/ppt", tags=["PPT管理"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识扩充"])
app.include_router(questions.router, prefix="/api/questions", tags=["题目管理"])
app.include_router(mistakes.router, prefix="/api/mistakes", tags=["错题本"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG
    )
