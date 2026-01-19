from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis
from config import settings

app = FastAPI(title="AutoKGS API", version="0.1.0")

# 允许跨域，方便前端开发
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 连接 Redis
try:
    r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
except Exception as e:
    print(f"Error connecting to Redis: {e}")
    r = None

# 统一健康检查逻辑
def health_check():
    redis_status = "connected"
    try:
        if r:
            r.ping()
        else:
            redis_status = "not initialized"
    except Exception as e:
        redis_status = f"failed: {str(e)}"
        
    return {
        "service": "AutoKGS Backend",
        "status": "running",
        "redis_connection": redis_status
    }

# 兼容两种路径，防止 Nginx/Proxy 转发问题
@app.get("/")
def read_root():
    return health_check()

@app.get("/api/")
def read_api_root():
    return health_check()

@app.get("/api/test")
def test_api():
    return {"message": "Hello from AutoKGS Backend!"}
