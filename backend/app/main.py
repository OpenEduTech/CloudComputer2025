from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import router as kg_router
import uvicorn
from app.db.neo4j_conn import init_neo4j, driver

# ========== 核心修改：直接初始化（模块加载时执行，全局生效） ==========
print("🔍 开始初始化Neo4j驱动...")
try:
    init_neo4j()
    print("✅ Neo4j驱动初始化完成（main.py全局初始化）")
except Exception as e:
    print(f"❌ Neo4j驱动初始化失败：{e}")
    raise  # 初始化失败则服务启动失败

# 初始化FastAPI
app = FastAPI(title="跨学科知识图谱智能体", version="1.0")


# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(kg_router)

# 健康检查接口（云原生稳定性）
@app.get("/health")
async def health_check():
    from app.db.neo4j_conn import driver
    neo4j_healthy = False
    try:
        if driver:
            driver.verify_connectivity()
            neo4j_healthy = True
    except:
        pass
    return {
        "status": "ok" if neo4j_healthy else "error",
        "services": {
            "backend": "running",
            "neo4j": neo4j_healthy
        },
        "version": "1.0"
    }

# 启动服务
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)