from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


def generate_session_name(text: str, fallback: str) -> str:
    """
    根据内容生成会话名，失败则回退到文件名。
    """
    if not settings.llm_api_key:
        return fallback
    sample = text[:800]
    prompt = ChatPromptTemplate.from_template(
        """
你是课程助手，请为以下内容生成一个简短会话名（不超过12个字）。只输出会话名，不要解释。
内容：{content}
"""
    )
    llm = ChatOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        temperature=0.2,
    )
    chain = prompt | llm | StrOutputParser()
    try:
        name = chain.invoke({"content": sample}).strip()
        return name or fallback
    except Exception:
        return fallback
