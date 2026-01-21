from pydantic import BaseModel
from dotenv import load_dotenv
import os


def _default_redis_url() -> str:
    # 自动识别运行环境：容器内使用 redis，非容器使用本地 127.0.0.1
    if os.path.exists("/.dockerenv"):
        return "redis://redis:6379/0"
    return "redis://127.0.0.1:6379/0"


# 读取 .env 环境变量，统一配置入口
load_dotenv()


class Settings(BaseModel):
    # LLM 配置
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    # Redis 与运行模式配置
    redis_url: str = os.getenv("REDIS_URL", _default_redis_url())
    use_langgraph: int = int(os.getenv("USE_LANGGRAPH", "1"))


settings = Settings()
