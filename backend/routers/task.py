from fastapi import APIRouter, BackgroundTasks, HTTPException
import uuid
import time
import json
import asyncio
import redis
from pydantic import BaseModel
from typing import Optional
from config import settings

router = APIRouter(
    prefix="/api/task",
    tags=["tasks"]
)

# Simple in-memory storage fallback
in_memory_store = {}

# 连接 Redis
try:
    redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
    redis_client.ping()
except Exception as e:
    print(f"Warning: Redis not available ({e}). Using in-memory storage.")
    redis_client = None

class TaskRequest(BaseModel):
    keyword: str
    params: Optional[dict] = {}

async def simulate_agent_processing(task_id: str, keyword: str):
    """
    模拟 Agent 的工作流程，逐步更新 Redis 状态
    """
    # 为了演示方便，我们假设用户输入的 Keyword 就是目标实体 ID（如果有对应数据）
    # 或者做一个简单的判断
    target_node_id = keyword if keyword else "Deep Learning"
    
    steps = [
        {"status": "PROCESSING", "step_index": 0, "progress": 5, "message": "任务已发送至 Redis 队列..."},
        {"status": "PROCESSING", "step_index": 1, "progress": 20, "message": "AI Worker (Agent) 已接单..."},
        {"status": "PROCESSING", "step_index": 2, "progress": 45, "message": f"正在检索关于 '{keyword}' 的资料..."},
        {"status": "PROCESSING", "step_index": 3, "progress": 70, "message": "正在提取实体与关系..."},
        {"status": "PROCESSING", "step_index": 4, "progress": 90, "message": "图谱构建完成，正在渲染..."},
        {
            "status": "SUCCESS", 
            "step_index": 5, 
            "progress": 100, 
            "message": "Completed", 
            "result_node_id": target_node_id, # 动态设置结果 ID
            "completed_at": int(time.time())
        }
    ]

    key = f"task:{task_id}"
    
    for step in steps:
        await asyncio.sleep(2) 
        if redis_client:
            redis_client.set(key, json.dumps(step))
        else:
            in_memory_store[key] = json.dumps(step)
            print(f"Updated task {task_id} to step {step.get('step_index')} (In-Memory)")

@router.post("")
async def create_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    接收任务，生成 TaskID，并启动后台模拟进程
    """
    task_id = str(uuid.uuid4())
    
    task_payload = {
        "task_id": task_id,
        "keyword": request.keyword,
        "params": request.params,
        "created_at": int(time.time())
    }
    
    if redis_client:
        redis_client.lpush("task_queue", json.dumps(task_payload))
        initial_status = {
            "status": "PROCESSING", 
            "step_index": 0, 
            "progress": 5, 
            "message": "任务已发送至 Redis 队列..."
        }
        redis_client.set(f"task:{task_id}", json.dumps(initial_status))
    else:
        initial_status = {
            "status": "PROCESSING", 
            "step_index": 0, 
            "progress": 5, 
            "message": "任务已初始化 (In-Memory)..."
        }
        in_memory_store[f"task:{task_id}"] = json.dumps(initial_status)

    # 传递 keyword 给模拟函数
    # background_tasks.add_task(simulate_agent_processing, task_id, request.keyword)
    return {"task_id": task_id}

@router.get("/{task_id}/status")
def get_task_status(task_id: str):
    """
    获取任务当前状态
    """
    key = f"task:{task_id}"
    
    if redis_client:
        status_json = redis_client.get(key)
    else:
        status_json = in_memory_store.get(key)
    
    if not status_json:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return json.loads(status_json)
