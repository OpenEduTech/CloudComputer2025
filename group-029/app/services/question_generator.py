import json
import os
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


def _build_prompt():
    # 生成题目提示词，要求输出 JSON
    return ChatPromptTemplate.from_template(
        """
你是一名机器学习课程助教。根据给定资料生成题目。要求：
1) 生成 {num_mcq} 道选择题 + {num_short} 道简答题。
2) 题目覆盖核心概念、公式、算法步骤，并体现难度梯度。
3) 难度梯度比例为 易:中:难 = {difficulty_ratio}，请尽量按比例控制。
4) 输出严格 JSON 数组，每个元素包含：qid, qtype, question, options(选择题需要), answer, explanation, evidence, difficulty(易/中/难)。
5) evidence 必须引用资料中的原文片段（可多条）。
6) 禁止输出除 JSON 以外的任何文本（不要 Markdown）。
示例（仅示例，不要复述）：[
  {{
    "qid": "mc_1",
    "qtype": "multiple_choice",
    "question": "示例题干",
    "options": ["A...", "B...", "C...", "D..."],
    "answer": "B",
    "explanation": "示例解析",
    "evidence": ["[c1] 示例证据"],
    "difficulty": "中"
  }}
]

资料片段：{context}
"""
    )


def _extract_json_text(raw: str) -> str:
    # 优先提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", raw, re.IGNORECASE)
    if match:
        return match.group(1)
    # 退化为截取首尾方括号内容
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]
    return raw


def generate_questions(chunks: list[dict], num_mcq: int, num_short: int, difficulty_ratio: str) -> tuple[list[dict], str]:
    if not settings.llm_api_key:
        raise ValueError("LLM_API_KEY 未配置")

    context = "\n\n".join([f"[{c['chunk_id']}]{c['text']}" for c in chunks])
    llm = ChatOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )
    prompt = _build_prompt()
    chain = prompt | llm | StrOutputParser()
    def _invoke_once() -> tuple[list[dict], str]:
        raw = chain.invoke(
            {
                "context": context,
                "num_mcq": num_mcq,
                "num_short": num_short,
                "difficulty_ratio": difficulty_ratio,
            }
        )
        json_text = _extract_json_text(raw)
        try:
            data = json.loads(json_text)
            if isinstance(data, list):
                return data, raw
        except json.JSONDecodeError:
            pass
        return [], raw

    data, raw = _invoke_once()
    if not data:
        # 失败时重试一次，减少偶发格式错误
        data, raw = _invoke_once()

    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "llm_raw.txt"), "w", encoding="utf-8") as f:
        f.write(raw)
    return [], raw
