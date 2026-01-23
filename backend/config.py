import os
from dotenv import load_dotenv

# 确保加载当前目录下的.env文件
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ 已加载配置文件: {env_path}")
else:
    print(f"⚠️ 未找到.env文件，使用默认配置: {env_path}")
    load_dotenv()

class AppConfig:
    # 1. 认证配置
    API_KEY = os.getenv("OPENAI_API_KEY")
    API_BASE = os.getenv("OPENAI_API_BASE")
    
    # 智谱AI配置 (保留，以防需要)
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
    ZHIPU_EMBEDDING_MODEL = os.getenv("ZHIPU_EMBEDDING_MODEL", "embedding-2")
    
    # 开发模式标志
    dev_mode_value = os.getenv("DEV_MODE", "True")
    DEV_MODE = dev_mode_value.strip().lower() in ["true", "1", "yes"]
    
    # 2. 模型配置
    CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "qwen-plus")
    EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-v1")
    
    # ✅ 新增：OCR 专用视觉模型
    OCR_MODEL = "qwen-vl-ocr-latest"
    
    # 3. 数据库配置
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

    # 4. ocr识别
    OCR_API_KEY = os.getenv("OCR_API_KEY") # 读取专用 Key

    @staticmethod
    def validate():
        if not AppConfig.API_KEY:
             print("⚠️ 未配置 OPENAI_API_KEY，部分 AI 功能将不可用")