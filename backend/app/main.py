from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import graph, task
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="跨学科知识图谱智能体 API",
    description="命题三：跨学科知识图谱生成与可视化系统后端",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    # 尝试更明确的配置
    swagger_ui_parameters={
        "syntaxHighlight.theme": "obsidian",
        "swagger_ui": "online"  # 显式尝试，某些版本需要
    }
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(graph.router, prefix="/api/graph", tags=["图谱"])
app.include_router(task.router, prefix="/api/task", tags=["任务"])

@app.get("/")
async def root():
    return {
        "message": "跨学科知识图谱智能体后端服务",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    from app.core.db import neo4j_driver, redis_client
    import traceback
    
    status = {"api": "healthy"}
    
    # 检查Neo4j连接
    try:
        with neo4j_driver.session() as session:
            result = session.run("RETURN 1")
            status["neo4j"] = "healthy" if result.single()[0] == 1 else "unhealthy"
    except Exception as e:
        status["neo4j"] = f"error: {str(e)}"
    
    # 检查Redis连接
    try:
        redis_client.ping()
        status["redis"] = "healthy"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"
    
    return status

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("🚀 跨学科知识图谱智能体后端服务启动")
    logger.info(f"📚 API文档: http://localhost:{settings.PORT}/docs")
    logger.info(f"🕸️ Neo4j浏览器: http://localhost:7474")
    
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    from app.core.db import neo4j_driver, redis_client
    neo4j_driver.close()
    redis_client.close()
    logger.info("👋 服务关闭，数据库连接已释放")