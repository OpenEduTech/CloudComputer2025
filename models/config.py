import os
from dotenv import load_dotenv
from typing import Dict, Any
from dataclasses import dataclass

load_dotenv()

@dataclass
class Config:
    # OpenAI配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "deepseek-ai/DeepSeek-V3.2")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
    
    # MongoDB配置
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB: str = "learning_agent"
    
    # 系统配置
    QUESTION_TYPES: tuple = ("multiple_choice", "short_answer", "true_false")
    DIFFICULTY_LEVELS: tuple = ("easy", "medium", "hard")
    
    # 调试和流式输出配置
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENABLE_STREAM: bool = os.getenv("ENABLE_STREAM", "True").lower() == "true"
    
    # 评估参数
    MAX_QUESTIONS_PER_SESSION: int = 10
    RETRY_LIMIT: int = 3
    
    # 提示词模板路径
    PROMPT_TEMPLATES_DIR: str = "prompt_templates"
    
    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set")