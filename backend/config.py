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
    
    # 智谱AI配置
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
    ZHIPU_EMBEDDING_MODEL = os.getenv("ZHIPU_EMBEDDING_MODEL", "embedding-2")
    ZHIPU_CHAT_MODEL = os.getenv("ZHIPU_CHAT_MODEL", "glm-4")
    
    # 开发模式标志
    DEV_MODE = os.getenv("DEV_MODE", "True").strip().lower() in ["true", "1", "yes"]
    
    # 允许在开发模式下跳过API验证
    SKIP_API_VALIDATION = DEV_MODE
    
    # 2. 模型配置
    CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "ecnu-plus")
    # ✅ 默认值修改为 ecnu-embedding-small
    EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "ecnu-embedding-small")
    
    # 3. 数据库配置
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    # Redis单节点配置
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    # Redis集群配置
    REDIS_CLUSTER_NODES = os.getenv("REDIS_CLUSTER_NODES", None)
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

    @staticmethod
    def validate():
        # 检查是否有可用的API密钥
        if AppConfig.ZHIPU_API_KEY:
            print(f"✅ 使用智谱AI API: {AppConfig.ZHIPU_CHAT_MODEL} (Embedding: {AppConfig.ZHIPU_EMBEDDING_MODEL})")
        elif AppConfig.API_KEY:
            if not AppConfig.API_BASE:
                print("⚠️ 警告: 未配置 OPENAI_API_BASE，将默认连接官方 OpenAI")
        else:
            raise ValueError("❌ 缺少 API Key，请检查 .env 文件中是否配置了 ZHIPU_API_KEY 或 OPENAI_API_KEY")