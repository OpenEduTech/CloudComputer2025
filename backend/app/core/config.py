"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "PPT学习助手"
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # 后端配置
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    # NOTE: 用 str 避免 pydantic-settings 对 List 类型强制 JSON 解析（本地 .env 常写成逗号分隔）
    BACKEND_CORS_ORIGINS: str = "http://localhost:8080,http://localhost:3000"
    
    # DeepSeek配置
    # 留空将导致 LLM 相关接口调用失败，但不阻塞服务启动（便于本地开发与前端联调）
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_EMBEDDING_MODEL: str = "deepseek-embedding"
    
    # ChromaDB配置
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8001
    CHROMA_PERSIST_DIRECTORY: str = "/app/data/chroma"
    
    # Redis配置
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 50  # MB
    # NOTE: 用 str 避免 pydantic-settings 对 List 类型强制 JSON 解析（本地 .env 常写成逗号分隔）
    ALLOWED_EXTENSIONS: str = ".ppt,.pptx,.pdf"
    UPLOAD_DIR: str = "/app/uploads"
    
    # 向量数据库配置
    EMBEDDING_MODEL: str = "deepseek-embedding"
    VECTOR_DIM: int = 1024
    
    # Agent配置
    MAX_RETRIES: int = 3
    TIMEOUT: int = 60
    TEMPERATURE: float = 0.7
    
    # 外部API配置
    WIKIPEDIA_API_ENABLED: bool = True
    ARXIV_API_ENABLED: bool = True
    SEMANTIC_SCHOLAR_API_ENABLED: bool = True
    OPENALEX_API_ENABLED: bool = True
    STACKEXCHANGE_API_ENABLED: bool = True
    BING_SEARCH_API_ENABLED: bool = False
    GOOGLE_CSE_API_ENABLED: bool = False

    # 外部API Key配置
    SEMANTIC_SCHOLAR_API_KEY: str | None = None
    OPENALEX_EMAIL: str | None = None
    STACKEXCHANGE_KEY: str | None = None
    BING_SEARCH_API_KEY: str | None = None
    GOOGLE_CSE_API_KEY: str | None = None
    GOOGLE_CSE_ENGINE_ID: str | None = None

    # OCR配置
    OCR_ENABLED: bool = False
    OCR_SEMANTIC_ENABLED: bool = True
    OUTLINE_SUMMARY_ENABLED: bool = True
    LLM_VALIDATION_ENABLED: bool = True
    TESSERACT_CMD: str | None = None

    # 本地预筛模型配置（可选）
    LOCAL_PREFILTER_ENABLED: bool = False
    LOCAL_PREFILTER_MODEL_PATH: str | None = None

    # 评分增强配置
    ANSWER_SIMILARITY_THRESHOLD: float = 0.55

    @property
    def allowed_extensions(self) -> List[str]:
        raw = (self.ALLOWED_EXTENSIONS or "").strip()
        if not raw:
            return [".ppt", ".pptx", ".pdf"]
        # 支持 JSON 数组 或 逗号分隔
        if raw.startswith("[") and raw.endswith("]"):
            try:
                import json

                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
        return [part.strip() for part in raw.split(",") if part.strip()]

    @property
    def cors_origins(self) -> List[str]:
        raw = (self.BACKEND_CORS_ORIGINS or "").strip()
        if not raw:
            return []
        if raw.startswith("[") and raw.endswith("]"):
            try:
                import json

                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
        return [part.strip() for part in raw.split(",") if part.strip()]

    @property
    def deepseek_api_base(self) -> str:
        base = (self.DEEPSEEK_API_BASE or "").strip() or "https://api.deepseek.com/v1"
        if not base.endswith("/v1"):
            base = base.rstrip("/") + "/v1"
        return base
    
    class Config:
        # 兼容两种启动方式：
        # - 在 backend/ 目录启动：读取 backend/.env
        # - 在项目根目录启动：读取 root/.env
        env_file = [".env", os.path.join("..", ".env")]
        case_sensitive = True
        # 允许 .env / 容器环境里出现前端变量（如 VITE_*）而不阻塞后端启动
        extra = "ignore"


# 创建全局配置实例
settings = Settings()
