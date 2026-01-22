from zai import ZhipuAiClient
from langchain_openai import ChatOpenAI
from app.core.config import settings

class LLMFactory:
    @staticmethod
    def get_zhipu_client() -> ZhipuAiClient:
        return ZhipuAiClient(api_key=settings.ZHIPU_API_KEY)
    
    @staticmethod
    def get_deepseek_llm():
        return ChatOpenAI(
            temperature=0.7,
            model="deepseek-reasoner",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
