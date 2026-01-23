from typing import List
import requests
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from config import settings

class ECNUEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str = None, base_url: str = None, model: str = "ecnu-embedding-small"):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = base_url or settings.LLM_API_BASE
        self.model = model
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY is not set. Please check your .env file or config.py")

    def __call__(self, input: Documents) -> Embeddings:
        """
        调用 ChatECNU Embedding API 生成向量
        """
        url = f"{self.base_url}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 批量处理以避免可能的 Payload 过大限制，这里简单起见假设一次调用可以处理
        # 如果 input 很大，建议在外部进行分批
        payload = {
            "model": self.model,
            "input": input
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 提取向量数据
            # 假设返回格式遵循 OpenAI 标准: { "data": [ { "embedding": [...] }, ... ] }
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings
            
        except Exception as e:
            print(f"Error calling ECNU Embedding API: {e}")
            # 返回空向量或抛出异常，视业务需求而定
            # 这里为了不中断流程，可能需要更健壮的重试机制
            raise e
