"""FastAPI主应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))  # 添加项目根目录

# 分别导入各模块，避免一个失败导致全部失败
try:
    from config import settings
except ImportError:
    class MockSettings:
        PROJECT_NAME = "ConceptGraph AI"
        VERSION = "1.0.0"
        DEBUG = True
        CORS_ORIGINS = ["http://localhost:3000"]
        API_PREFIX = "/api/v1"
        HOST = "0.0.0.0"
        PORT = 8888
    settings = MockSettings()
    print("[WARNING] config模块加载失败，使用Mock配置")

# 优先使用backend/api/routes（包含Wikipedia支持）
try:
    # 使用动态路径导入backend目录下的routes
    import importlib.util
    routes_path = Path(__file__).parent / "api" / "routes.py"
    spec = importlib.util.spec_from_file_location("backend_routes", str(routes_path))
    backend_routes_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend_routes_module)
    routes_router = backend_routes_module.router
    print("[INFO] 使用backend/api/routes（包含Wikipedia支持）")
except Exception as e:
    print(f"[WARNING] backend/api/routes加载失败: {e}")
    routes_router = None

try:
    from database import neo4j_client, redis_client
except ImportError:
    class MockClient:
        async def connect(self): pass
        async def disconnect(self): pass
        async def is_connected(self): return False
    neo4j_client = MockClient()
    redis_client = MockClient()
    print("[WARNING] database模块加载失败，使用Mock客户端")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库连接
    print("[INFO] 启动应用，初始化数据库连接...")
    try:
        await neo4j_client.connect()
        print("[SUCCESS] Neo4j连接成功")
    except Exception as e:
        print(f"[WARNING] Neo4j连接失败: {e}")
    
    try:
        await redis_client.connect()
        print("[SUCCESS] Redis连接成功")
    except Exception as e:
        print(f"[WARNING] Redis连接失败: {e}")
    
    yield
    
    # 关闭时清理资源
    print("[INFO] 关闭应用，清理资源...")
    await neo4j_client.disconnect()
    await redis_client.disconnect()
    print("[SUCCESS] 资源清理完成")


# 创建FastAPI应用实例
app = FastAPI(
    title=getattr(settings, 'PROJECT_NAME', 'ConceptGraph AI'),
    version=getattr(settings, 'VERSION', '1.0.0'),
    description="跨学科知识图谱智能体 API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（如果存在）
if routes_router:
    app.include_router(routes_router, prefix=getattr(settings, 'API_PREFIX', '/api/v1'))
    print(f"[INFO] 路由已注册到 {getattr(settings, 'API_PREFIX', '/api/v1')}")

# 注册AI问答路由（已集成到routes.py中）
# AI问答功能现在通过 /api/v1/ai/chat 端点提供

# 根路径
@app.get("/")
async def root():
    """API根路径"""
    return {
        "service": getattr(settings, 'PROJECT_NAME', 'ConceptGraph AI'),
        "version": getattr(settings, 'VERSION', '1.0.0'),
        "status": "running",
        "docs": "/docs",
        "api": getattr(settings, 'API_PREFIX', '/api/v1')
    }

# 健康检查接口
@app.get("/health")
async def health_check():
    """健康检查 - 用于Docker/K8S健康探针"""
    return {"status": "healthy"}

# 就绪检查接口
@app.get("/ready")
async def readiness_check():
    """就绪检查 - 检查依赖服务是否可用"""
    try:
        neo4j_ok = await neo4j_client.is_connected()
        redis_ok = await redis_client.is_connected()
        
        if neo4j_ok and redis_ok:
            return {
                "status": "ready",
                "services": {
                    "neo4j": "connected",
                    "redis": "connected"
                }
            }
        
        return {
            "status": "not ready",
            "services": {
                "neo4j": "connected" if neo4j_ok else "disconnected",
                "redis": "connected" if redis_ok else "disconnected"
            }
        }, 503
    except:
        return {"status": "ready", "services": {"neo4j": "mock", "redis": "mock"}}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=getattr(settings, 'HOST', '0.0.0.0'),
        port=getattr(settings, 'PORT', 8000),
        reload=True,
        reload_excludes=["*.pyc", "__pycache__", "*.log", "test_*.py"],  # 排除不必要的重载
        log_level="info"
    )
