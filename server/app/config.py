"""
PatPat-Inconsistency-Hunter 配置模块
定义系统运行所需的所有配置项
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """系统配置类"""
    
    # 应用基础配置
    APP_NAME: str = "PatPat-Inconsistency-Hunter"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # DeepSeek API 配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # Redis 配置
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # 数据库配置 (PostgreSQL)
    DATABASE_URL: str = "postgresql://patpat:patpat123@postgres:5432/patpat_db"
    
    # JWT 认证配置
    SECRET_KEY: str = "patpat-secret-key-please-change-in-production-env"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    
    # 文档处理配置
    MAX_DOCUMENT_LENGTH: int = 100000  # 最大文档长度（字符数）
    MIN_DOCUMENT_LENGTH: int = 100    # 最小文档长度（字符数）
    CHUNK_SIZE: int = 2000             # 文档分块大小
    CHUNK_OVERLAP: int = 200           # 分块重叠大小
    
    # LLM 配置
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT: int = 120
    
    # 并发配置
    MAX_CONCURRENCY: int = 5
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/patpat.log"
    
    # 视觉模型配置 (InternVL)
    USE_VISION_MODEL: bool = True  # 是否启用视觉模型处理图片
    VISION_MODEL_ROOT: str = "./models"  # 模型目录
    VISION_MODEL_NAME: str = "InternVL3_5-4B-HF"  # 模型名称（4B版本）
    VISION_MAX_CONCURRENCY: int = 2  # 视觉模型并发数（通常GPU显存有限）
    
    # LangGraph 配置
    USE_LANGGRAPH_ENGINE: bool = True  # 是否使用 LangGraph 增强引擎
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 导出配置实例
settings = get_settings()

