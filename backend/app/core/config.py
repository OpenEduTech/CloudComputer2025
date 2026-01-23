from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Learning Agent"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-please-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day for dev
    
    # Database
    # 优先使用环境变量，Docker 部署时会自动使用 mongo:27017
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "learning_agent_db")
    
    # AI Keys
    # 优先使用环境变量，没有则使用默认值
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "sk-c20873c2404043a6bd935d590621dfe1")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    ZHIPU_API_KEY: str = os.getenv("ZHIPU_API_KEY", "f7f33a87ea1a43ef8eb40ba7f21ddd02.t3Im7AVwFtRiY4ZY")

    class Config:
        env_file = ".env"

settings = Settings()
