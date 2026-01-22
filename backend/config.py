"""配置文件"""
import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的.env文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """应用配置"""
    
    # 项目信息
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "ConceptGraph AI")
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # 服务器配置
    HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("BACKEND_PORT", "8888"))
    API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
    
    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    
    # 数据库配置
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "conceptgraph")
    
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))
    
    # Mock模式（数据库Mock，但API仍真实调用）
    MOCK_DB: bool = os.getenv("MOCK_DB", "false").lower() == "true"
    
    # Agent服务地址
    AGENT_API_URL: str = os.getenv("AGENT_API_URL", "http://localhost:5000")


settings = Settings()
