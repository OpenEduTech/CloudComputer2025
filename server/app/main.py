"""
PatPat-Inconsistency-Hunter 主应用入口
FastAPI 应用配置和启动
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from .config import settings
from .api.routes import router as api_router
from .api.collaboration_routes import router as collaboration_router
from .api.auth_routes import router as auth_router
from .api.document_routes import router as document_router
from .utils.logger import logger
from .utils.redis_client import get_redis_client, close_redis_client
from .utils.db_session import init_db, close_db
from .services.llm_client import close_llm_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    处理启动和关闭时的资源初始化和清理
    """
    # 启动时
    logger.info(f"正在启动 {settings.APP_NAME} v{settings.APP_VERSION}...")
    
    # 初始化Redis连接
    try:
        redis_client = await get_redis_client()
        logger.info("Redis连接初始化成功")
    except Exception as e:
        logger.warning(f"Redis连接初始化失败（服务将继续运行，但部分功能可能受限）: {e}")
    
    # 初始化数据库表
    try:
        await init_db()
        logger.info("数据库表初始化成功")
    except Exception as e:
        logger.warning(f"数据库初始化失败: {e}")
    
    logger.info(f"{settings.APP_NAME} 启动完成")
    
    yield
    
    # 关闭时
    logger.info(f"正在关闭 {settings.APP_NAME}...")
    
    # 关闭Redis连接
    await close_redis_client()
    
    # 关闭LLM客户端
    await close_llm_client()
    
    # 关闭数据库连接
    await close_db()
    
    logger.info(f"{settings.APP_NAME} 已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## PatPat-Inconsistency-Hunter 长文本事实卫士

### 功能特点

- 🔍 **事实提取**: 自动从长文档中提取关键事实（数据、日期、结论、人名等）
- ⚡ **冲突检测**: 智能扫描全文，发现前后不一致的描述
- ✅ **溯源校验**: 分析冲突事实，提供修正建议
- 📊 **可视化仪表盘**: 直观展示分析结果

### API 使用流程

1. 调用 `POST /api/analyze` 提交文档分析任务
2. 使用 `GET /api/task/{task_id}/status` 查询任务进度
3. 任务完成后，通过以下接口获取结果：
   - `GET /api/task/{task_id}/result` - 获取分析结果摘要
   - `GET /api/task/{task_id}/facts` - 获取提取的事实列表
   - `GET /api/task/{task_id}/conflicts` - 获取检测到的冲突列表

### 技术栈

- 后端: FastAPI + DeepSeek LLM
- 数据库: Redis (事实黑板) + PostgreSQL (持久化)
- 部署: Docker + Docker Compose
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix="/api")
app.include_router(collaboration_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(document_router, prefix="/api")

# 静态文件服务（图片上传）
import os
from pathlib import Path

# 头像上传目录（映射到 uploads，避免重建容器后丢失）
static_dir = Path("uploads")
static_dir.mkdir(exist_ok=True)
(static_dir / "avatars").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 其他上传目录
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
(uploads_dir / "images").mkdir(exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory="uploads"), name="uploads")


# 根路径
@app.get("/", tags=["根"])
async def root():
    """
    API根路径
    
    返回服务基本信息
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "长文本事实卫士智能体 - 确保长文档事实一致性的中间件",
        "docs": "/docs",
        "status": "running",
    }


def run_server():
    """运行服务器"""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    run_server()

