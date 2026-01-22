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
    
    @property
    def AVAILABLE_SUBJECTS(self):
        """
        动态获取 data 目录下的所有学科（文件夹名称）。
        仅返回一级目录。
        """
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        try:
            if not os.path.exists(data_dir):
                # Fallback defaults if data dir doesn't exist yet
                return [
                    "Language_and_Symbolic_Systems",
                    "Humans_and_Cognition", 
                    "Formal_Sciences_and_Computation",
                    "Natural_Sciences"
                ]
            
            subjects = [
                d for d in os.listdir(data_dir) 
                if os.path.isdir(os.path.join(data_dir, d)) and not d.startswith('.')
            ]
            return subjects if subjects else ["General"]
        except Exception as e:
            print(f"Error reading subjects from data dir: {e}")
            return ["General"]

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
