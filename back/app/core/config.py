from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any
import os

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "跨学科知识图谱智能体"
    PORT: int = 8000
    DEBUG: bool = True
    
    # 🎯 关键配置：Mock模式开关
    USE_MOCK: bool = os.getenv("USE_MOCK", "False").lower() == "true"  # 默认使用Agent服务
    
    # Agent服务配置
    AGENT_SERVICE_URL: str = os.getenv("AGENT_SERVICE_URL", "http://localhost:8001")
    AGENT_TIMEOUT: int = int(os.getenv("AGENT_TIMEOUT", "300"))  # 快速API调用超时
    AGENT_LONG_TIMEOUT: int = int(os.getenv("AGENT_LONG_TIMEOUT", "600"))  # 后台长时间任务超时
    
    # Agent服务调用配置
    AGENT_CONFIG: Dict[str, Any] = {
        "constraints": {
            "max_nodes": int(os.getenv("AGENT_MAX_NODES", "30")),
            "max_edges": int(os.getenv("AGENT_MAX_EDGES", "50")),
            "min_confidence": float(os.getenv("AGENT_MIN_CONFIDENCE", "0.55"))
        },
        "output": {
            "format": "graphjson",
            "schema_version": "v1.1"
        }
    }
    
    # Neo4j配置
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password123"
    
    # Redis配置
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # 缓存配置
    CACHE_TTL: int = 86400  # 24小时
    
    # LLM配置（为A的Agent服务准备，但在后端中不使用）
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: Optional[str] = os.getenv("DEEPSEEK_BASE_URL", "")
    DEEPSEEK_MODEL: Optional[str] = os.getenv("DEEPSEEK_MODEL", "")
    LLM_TIMEOUT: Optional[int] = int(os.getenv("LLM_TIMEOUT", "300"))
    LLM_MAX_RETRIES: Optional[int] = int(os.getenv("LLM_MAX_RETRIES", "3"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 允许额外的环境变量，不进行验证

settings = Settings()