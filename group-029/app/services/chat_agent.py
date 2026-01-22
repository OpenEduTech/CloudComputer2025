from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


def chat_answer(chunks: list[dict], message: str) -> tuple[str, list[str]]:
    """
    基于检索片段回答问题，并返回证据来源。
    """
    if not settings.llm_api_key:
        raise ValueError("LLM_API_KEY 未配置")
    context = "\n\n".join([f"[{c['chunk_id']}]{c['text']}" for c in chunks])
    prompt = ChatPromptTemplate.from_template(
        """
你是学习评估智能体，请基于给定资料回答用户问题。
要求：
1) 只基于资料回答，不确定时要说明资料不足。
2) 回答尽量简洁、清晰。
3) 禁止编造资料中不存在的内容。

资料片段：{context}

用户问题：{question}
"""
    )
    llm = ChatOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": message}).strip()
    # 返回片段摘要，便于前端展示证据来源
    sources = [f"[{c['chunk_id']}] {c['text'][:120]}" for c in chunks]
    return answer, sources
