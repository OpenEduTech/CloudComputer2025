"""
LLM模型工厂
统一创建LLM实例，使用SiliconFlow - DeepSeek配置
"""

from langchain_openai import ChatOpenAI
from app.config import settings


def create_llm(**kwargs) -> ChatOpenAI:
    """
    创建LLM实例（统一使用SiliconFlow - DeepSeek配置）
    
    Args:
        **kwargs: 可选的参数覆盖（如temperature等）
        
    Returns:
        ChatOpenAI实例
    """
    # 使用配置中的默认值，允许通过kwargs覆盖
    api_key = kwargs.pop('api_key', settings.LLM_API_KEY or settings.OPENAI_API_KEY)
    base_url = kwargs.pop('base_url', settings.LLM_BASE_URL or settings.OPENAI_BASE_URL)
    model = kwargs.pop('model', settings.LLM_MODEL or settings.OPENAI_MODEL)
    temperature = kwargs.pop('temperature', settings.LLM_TEMPERATURE)
    
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        **kwargs
    )
