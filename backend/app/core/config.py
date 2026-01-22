from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Learning Agent"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-please-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day for dev
    
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "learning_agent_db"
    
    # AI Keys
    # Default from doc.md
    DEEPSEEK_API_KEY: str = "sk-c20873c2404043a6bd935d590621dfe1"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    ZHIPU_API_KEY: str = "f7f33a87ea1a43ef8eb40ba7f21ddd02.t3Im7AVwFtRiY4ZY"

    class Config:
        env_file = ".env"

settings = Settings()
