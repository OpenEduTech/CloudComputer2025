"""
应用配置管理
使用Pydantic Settings进行配置管理
"""

from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    """应用配置类"""
    
    # LLM API配置（使用SiliconFlow - DeepSeek模型）
    LLM_API_KEY: str = "sk-lfuvqnvbwgtxkfdnpdinfvihjxapsevyhlfqgvqorqtvfqfv"
    LLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    LLM_MODEL: str = "deepseek-ai/DeepSeek-V3.2-Exp"
    LLM_TEMPERATURE: float = 0.7
    
    # 兼容性配置（保留OpenAI相关字段，用于环境变量）
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.siliconflow.cn/v1"
    OPENAI_MODEL: str = "deepseek-ai/DeepSeek-V3.2-Exp"
    
    # Milvus向量数据库配置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_NAME: str = "ppt_chunks"
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # 服务配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    
    # 文件路径配置
    UPLOAD_DIR: str = "./uploads"
    OUTPUT_DIR: str = "./output"
    LOG_DIR: str = "./logs"
    
    # 嵌入模型配置
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # 外部API配置
    ARXIV_API_KEY: str = ""
    WIKIPEDIA_LANG: str = "zh"
    
    # 安全配置
    SECRET_KEY: str = "your_secret_key_here"
    ALLOWED_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:8000"]
    
    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """解析ALLOWED_ORIGINS，支持逗号分隔的字符串或列表"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
