"""FastAPI应用主入口"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from api.routes import router
from shared.error_codes import ErrorCode, get_error_message

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 ConceptGraph AI API 启动中...")
    logger.info(f"📍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"🔑 OpenAI API Key: {'已配置' if os.getenv('OPENAI_API_KEY') else '未配置'}")
    logger.info(f"🔑 OpenRouter API Key: {'已配置' if os.getenv('OPENROUTER_API_KEY') else '未配置'}")
    
    yield
    
    # 关闭时
    logger.info("🛑 ConceptGraph AI API 关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title="ConceptGraph AI API",
    description="跨学科知识图谱智能体 - Agent接口服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS配置
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(router, prefix="/api/v1")


# 根路径
@app.get("/")
async def root():
    """API根路径"""
    return {
        "service": "ConceptGraph AI API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "discover": "/api/v1/agent/discover",
            "verify": "/api/v1/agent/verify",
            "expand": "/api/v1/agent/expand"
        }
    }


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY"))
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": ErrorCode.UNKNOWN_ERROR,
            "message": get_error_message(ErrorCode.UNKNOWN_ERROR),
            "details": str(exc) if os.getenv("ENVIRONMENT") == "development" else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
