from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import task, graph
from database.neo4j_utils import close_driver

app = FastAPI(title="AutoKGS API", version="0.1.0")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(task.router)
app.include_router(graph.router)

@app.on_event("shutdown")
def shutdown_event():
    close_driver()

@app.get("/")
def read_root():
    return {"status": "AutoKGS Backend Running"}

@app.get("/api/")
def read_api_root():
    return {"status": "AutoKGS API Running"}
