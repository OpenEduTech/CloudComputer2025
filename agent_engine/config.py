import os

class Settings:
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    CHROMA_SERVER_HOST = os.getenv("CHROMA_SERVER_HOST", "localhost")
    CHROMA_SERVER_PORT = int(os.getenv("CHROMA_SERVER_PORT", 8000))
    # 切换为 ecnu-embedding-small，维度 1024
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "ecnu-embedding-small")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_API_BASE = os.getenv("LLM_API_BASE", "https://chat.ecnu.edu.cn/open/api/v1")
    KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
    KIMI_API_BASE = os.getenv("KIMI_API_BASE", "https://api.moonshot.cn/v1")
    
    # Neo4j Settings
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    '''
    CHATECNU请求头示例
    POST https://chat.ecnu.edu.cn/open/api/v1/chat/completions
    Content-Type: application/json
    Authorization: Bearer <yourapikey>

    {
        "messages": [{
            "role": "system",
            "content": "你是华东师范大学大模型ChatECNU"
        }, {
            "role": "user",
            "content": "你好呀"
        }],
        "stream": false,
        "model": "ecnu-plus"
    }
    '''

settings = Settings()
