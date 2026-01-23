from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import redis
import os
import json
import uuid
import asyncio
import utils 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

r = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=6379,
    decode_responses=True
)

# --- 数据模型 ---

class UserAuth(BaseModel):
    username: str
    password: str

class BatchGenerateRequest(BaseModel):
    username: str
    # 彻底去掉 set_id，只传配置
    config: Dict[str, Dict[str, int]] 

class MistakeRequest(BaseModel):
    username: str
    set_id: Optional[str] = None
    question: dict
    user_answer: str

class GradeRequest(BaseModel):
    username: str
    set_id: Optional[str] = None
    question_data: dict
    user_answer: str

# --- 1. 用户模块 ---

@app.post("/api/register")
def register(user: UserAuth):
    if r.hexists("users", user.username):
        raise HTTPException(status_code=400, detail="用户已存在")
    r.hset("users", user.username, user.password)
    return {"status": "success"}

@app.post("/api/login")
def login(user: UserAuth):
    db_pass = r.hget("users", user.username)
    if db_pass == user.password:
        return {"status": "success", "username": user.username}
    raise HTTPException(status_code=401, detail="密码错误")

# --- 2. 资料上传（自动建类并关联上下文） ---

@app.post("/api/upload_to_cache")
async def upload_to_cache(username: str, file: UploadFile = File(...)):
    """上传文件：解析、以文件名建类、标记为最近上传"""
    content = await file.read()
    if file.filename.lower().endswith(".pdf"):
        text = utils.extract_text_from_pdf_bytes(content)
    else:
        text = utils.extract_text_from_txt_bytes(content)
    
    if not text:
        raise HTTPException(status_code=400, detail="解析失败")

    set_id = str(uuid.uuid4())
    set_meta = {
        "id": set_id,
        "name": file.filename,
        "created_at": str(uuid.uuid1().time)
    }

    # 存储分类信息
    r.hset(f"sets:{username}", set_id, json.dumps(set_meta, ensure_ascii=False))
    r.set(f"text_content:{set_id}", text)
    # 标记为该用户的“当前活跃分类”
    r.set(f"recent_set:{username}", set_id) 

    return {"status": "success", "set_id": set_id, "category_name": file.filename}

# --- 3. 批量出题（不传 ID，嵌套格式） ---

@app.post("/api/generate_batch")
async def generate_batch(req: BatchGenerateRequest):
    """自动寻找最近文档并按嵌套配置出题"""
    # 自动识别 ID
    target_id = r.get(f"recent_set:{req.username}")
    if not target_id:
        raise HTTPException(status_code=404, detail="请先上传文档")

    text = r.get(f"text_content:{target_id}")
    tasks = []
    
    # 解析嵌套 JSON
    for q_type, diff_config in req.config.items():
        for diff_level, count in diff_config.items():
            difficulty = int(diff_level)
            if q_type == "mcq":
                for _ in range(count):
                    tasks.append(asyncio.to_thread(utils.generate_one_mcq, text, difficulty))
            elif q_type == "short":
                for _ in range(count):
                    tasks.append(asyncio.to_thread(utils.generate_one_short, text, difficulty))

    results = await asyncio.gather(*tasks)
    
    final_questions = []
    for q in results:
        if q:
            # 存入历史库
            r.rpush(f"questions:{target_id}", json.dumps(q, ensure_ascii=False))
            final_questions.append(q)

    return {"status": "success", "set_id": target_id, "questions": final_questions}

# --- 4. 实时反馈与错题逻辑 ---

@app.post("/api/save_mistake")
def save_mistake(req: MistakeRequest):
    """选择题选错：实时给分析并入库"""
    target_id = req.set_id or r.get(f"recent_set:{req.username}")
    
    ai_feedback = utils.get_mistake_feedback(
        req.question.get('question'), 
        req.question.get('reference_answer'), 
        req.user_answer
    )
    
    record = {"q": req.question, "my_ans": req.user_answer, "ai_feedback": ai_feedback}
    r.lpush(f"mistakes:{target_id}", json.dumps(record, ensure_ascii=False))
    
    return {"ai_feedback": ai_feedback, "correct": req.question.get('reference_answer')}

@app.post("/api/grade_short")
def grade_short(req: GradeRequest):
    """简答题阅卷：不及格（<60）自动入库"""
    result = utils.grade_short_answer(
        req.question_data.get('question'), 
        req.question_data.get('reference_answer'), 
        req.user_answer
    )
    
    score = result.get('score', 0)
    comment = result.get('comment', "无评语")
    
    if score < 60:
        target_id = req.set_id or r.get(f"recent_set:{req.username}")
        record = {"type": "short", "q": req.question_data, "my_ans": req.user_answer, "ai_feedback": comment}
        r.lpush(f"mistakes:{target_id}", json.dumps(record, ensure_ascii=False))
        
    return {"score": score, "comment": comment}

# --- 5. 历史查看 ---

@app.get("/api/sets/list")
def get_user_sets(username: str):
    data = r.hgetall(f"sets:{username}")
    result = []
    for sid, meta_json in data.items():
        meta = json.loads(meta_json)
        meta['count'] = r.llen(f"questions:{sid}")
        result.append(meta)
    return sorted(result, key=lambda x: x['created_at'], reverse=True)

@app.get("/api/sets/detail")
def get_set_questions(set_id: str):
    items = r.lrange(f"questions:{set_id}", 0, -1)
    return [json.loads(i) for i in items]

@app.get("/api/mistakes/list")
def get_set_mistakes(set_id: str):
    items = r.lrange(f"mistakes:{set_id}", 0, -1)
    return [json.loads(i) for i in items]