import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # API配置
    siliconflow_api_key: str = Field(..., env="SILICONFLOW_API_KEY")
    siliconflow_base_url: str = Field("https://api.siliconflow.cn/v1", env="SILICONFLOW_BASE_URL")
    siliconflow_model: str = Field("deepseek-ai/DeepSeek-V3.2-Exp", env="SILICONFLOW_MODEL")

    # 应用配置
    api_port: int = Field(8010, env="API_PORT")
    web_port: int = Field(8501, env="WEB_PORT")
    debug: bool = Field(True, env="DEBUG")
    upload_folder: str = Field("uploads", env="UPLOAD_FOLDER")
    max_upload_size: int = Field(100 * 1024 * 1024, env="MAX_UPLOAD_SIZE")
    allowed_extensions: List[str] = Field(["pptx", "ppt", "pdf"])

    # Milvus 配置
    milvus_host: str = Field("milvus-standalone", env="MILVUS_HOST")
    milvus_port: int = Field(19530, env="MILVUS_PORT")
    milvus_collection: str = Field("ppt_content", env="MILVUS_COLLECTION")
    milvus_embedding_dim: int = Field(384, env="MILVUS_EMBEDDING_DIM")

    # 数据库配置
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")
    postgres_url: str = Field("postgresql://admin:admin123@postgres:5432/ppt_agent", env="POSTGRES_URL")

    # 安全配置
    cors_origins: List[str] = Field(["http://localhost:8501", "http://localhost:8010"])

    # Milvus 超时设置
    milvus_timeout: int = Field(30, env="MILVUS_TIMEOUT")

    # HTTP 客户端设置
    httpx_timeout: int = Field(180, env="HTTPX_TIMEOUT")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()