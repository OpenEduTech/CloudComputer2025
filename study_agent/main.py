from fastapi import FastAPI, UploadFile, File, HTTPException
import shutil
import os
import redis
import json
from core_logic import StudyAgent

app = FastAPI(title="云原生智能学习评估系统")
agent = StudyAgent()

# 连接 Redis (Docker 内部连接地址为 'redis')
try:
    r = redis.Redis(host='redis', port=6379, decode_responses=True)
except:
    r = None

@app.post("/upload", summary="1. 上传 PDF 并生成练习题")
async def upload_and_generate(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        context = agent.parse_pdf(temp_path)
        questions = agent.generate_comprehensive_questions(context)
        
        if not questions:
            raise HTTPException(status_code=500, detail="AI 生成题目失败")

        # 将生成的题目存入 Redis，有效期 1 小时
        if r:
            r.set("current_exam", json.dumps(questions), ex=3600)

        return {"status": "success", "questions": questions}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/submit", summary="2. 提交答案并智能判卷")
async def submit_answer(index: int, user_answer: str):
    """
    index: 题号 (1, 2, 3...)
    user_answer: 用户的回答内容
    """
    if not r:
        raise HTTPException(status_code=500, detail="Redis 服务未连接")
        
    exam_data = r.get("current_exam")
    if not exam_data:
        raise HTTPException(status_code=400, detail="请先上传资料生成题目")
    
    questions = json.loads(exam_data)
    
    # 兼容性匹配：寻找对应题目的容错逻辑
    target_q = None
    for idx, q in enumerate(questions):
        # 即使 AI 没给 index，我们也通过数组下标保底匹配
        q_idx = q.get('index') or q.get('id') or (idx + 1)
        if str(q_idx) == str(index):
            target_q = q
            break
            
    if not target_q:
        raise HTTPException(status_code=404, detail=f"未找到题号 {index}")

    # 调用 AI 判卷
    result = agent.grade_answer(
        target_q['question'], 
        target_q['answer'], 
        user_answer
    )

    # 弱点记忆逻辑：自动将错题存入错题本列表
    if not result.get('is_correct') or result.get('score', 100) < 60:
        wrong_item = {
            "question": target_q['question'],
            "standard_answer": target_q['answer'],
            "user_answer": user_answer,
            "feedback": result.get('feedback')
        }
        r.lpush("wrong_question_book", json.dumps(wrong_item))

    return result

@app.get("/wrong_book", summary="3. 查看个性化错题本")
async def get_wrong_book():
    if not r:
        return {"error": "Redis 库未连接"}
    # 从 Redis 列表读取所有错题记录
    data = r.lrange("wrong_question_book", 0, -1)
    return [json.loads(item) for item in data]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)