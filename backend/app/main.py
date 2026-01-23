import os
import json
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 初始化 FastAPI ---
app = FastAPI(title="Learning Agent API")

# --- 数据库连接 (MongoDB) ---
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://mongo:27017")
try:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client["learning_agent_db"]
    quiz_collection = db["quizzes"]  # 存放生成的试卷
    logger.info(f"Connected to MongoDB at {MONGO_URL}")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")

# --- LangChain 模型初始化 ---
# 这里的 API Key 会从 docker-compose 的环境变量里自动读取
llm = ChatOpenAI(
    model="deepseek-chat", # 如果用 DeepSeek，这里改 "deepseek-chat"
    temperature=0.7,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_API_BASE")
)

# --- 定义数据结构 (Pydantic) ---

# 1. 单道选择题的结构
class Question(BaseModel):
    id: int = Field(description="题目序号")
    question: str = Field(description="题干内容")
    options: List[str] = Field(description="4个选项列表，例如 ['A. xxx', 'B. xxx', ...]")
    correct_answer: str = Field(description="正确答案，例如 'A'")
    explanation: str = Field(description="答案解析，解释为什么选这个")

# 2. 整个试卷的结构
class QuizOutput(BaseModel):
    topic: str = Field(description="根据内容总结的主题")
    questions: List[Question] = Field(description="生成的问题列表")

# 3. 前端传来的请求格式
class InputData(BaseModel):
    text: str

# --- 核心 Prompt 设计 ---
parser = PydanticOutputParser(pydantic_object=QuizOutput)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的大学助教。你的任务是根据用户提供的学习资料，出这份资料的考核试题。"),
    ("user", "请根据以下文本内容，生成 3 道单项选择题。\n\n学习资料：\n{text}\n\n要求：\n1. 题目要有针对性，覆盖核心考点。\n2. 解析要详细。\n3. {format_instructions}")
])

# --- API 接口 ---

@app.get("/")
def read_root():
    """健康检查接口"""
    # 检查数据库连接
    db_status = "Connected"
    try:
        client.admin.command('ping')
    except:
        db_status = "Disconnected"
    return {"status": "Backend Running", "database": db_status}

@app.post("/generate_quiz")
def generate_quiz(data: InputData):
    """核心功能：调用 LLM 生成题目并存入数据库"""
    if not data.text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    logger.info("Received request to generate quiz.")
    
    try:
        # 1. 组装 Chain
        chain = prompt_template | llm | parser
        
        # 2. 调用大模型 (这是最耗时的一步)
        result = chain.invoke({
            "text": data.text[:3000], # 截断一下防止Token超标
            "format_instructions": parser.get_format_instructions()
        })
        
        # 3. 转换成字典
        quiz_data = result.dict()
        
        # 4. 【关键】持久化存入 MongoDB (满足作业要求)
        insert_result = quiz_collection.insert_one(quiz_data)
        quiz_data["_id"] = str(insert_result.inserted_id) #不仅返回题目，还返回数据库ID
        
        logger.info("Quiz generated and saved successfully.")
        return quiz_data

    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        # 如果解析失败，返回一个模拟的错误信息方便调试
        raise HTTPException(status_code=500, detail=str(e))

# 添加到 backend/app/main.py 文件末尾

@app.get("/get_history")
def get_history():
    """从 MongoDB 读取生成过的历史题目"""
    try:
        # 查询所有记录，按时间倒序排列，限制返回最近 10 条
        cursor = quiz_collection.find().sort("_id", -1).limit(10)
        quizzes = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"]) # ObjectId 转字符串
            quizzes.append(doc)
        return quizzes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))