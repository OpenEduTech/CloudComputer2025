import json
import os
import re

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


def _extract_json_text(raw: str) -> str:
    # 提取 JSON 数组/对象，避免模型输出混入说明文本
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if match:
        return match.group(1)
    return raw


def _build_check_prompt() -> ChatPromptTemplate:
    # 判卷校验提示词，减少幻觉与不一致评分
    return ChatPromptTemplate.from_template(
        """
你是判卷结果的校验官。请检查评分结果是否与题目、参考答案、学生答案一致。
要求：
1) 若发现评分/对错不一致，修正为合理结果。
2) 保留原有 qid，不新增或删除条目。
3) 输出严格 JSON 数组，每个元素包含：qid, is_correct, score, explanation。
4) 禁止输出除 JSON 以外的任何文本（不要 Markdown）。

题目：{questions}

学生答案：{answers}

参考答案：{reference}

原始评分：{graded}
"""
    )


def grade_answers(questions: list[dict], answers: list[dict], contexts: list[dict]) -> tuple[list[dict], str]:
    if not settings.llm_api_key:
        raise ValueError("LLM_API_KEY 未配置")

    prompt = ChatPromptTemplate.from_template(
        """
你是严格的机器学习助教，请根据题目与学生答案进行判卷。
评分规则：
1) 选择题：答案匹配则满分 1，否则 0。
2) 简答题：满分 2，根据覆盖要点给分（0/1/2），并给出简洁解析。
3) 必须输出 JSON 数组，每个元素包含：qid, is_correct, score, explanation。
4) 禁止输出除 JSON 以外的任何文本（不要 Markdown）。
示例（仅示例，不要复述）：[
  {{"qid": "mc_1", "is_correct": true, "score": 1, "explanation": "示例解析"}}
]

题目：{questions}

学生答案：{answers}

参考资料（按 qid 对应）：{contexts}
"""
    )

    llm = ChatOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )
    chain = prompt | llm | StrOutputParser()
    raw = chain.invoke({"questions": questions, "answers": answers, "contexts": contexts})
    json_text = _extract_json_text(raw)
    try:
        data = json.loads(json_text)
        if isinstance(data, list):
            # 进入校验环节
            check_prompt = _build_check_prompt()
            check_chain = check_prompt | llm | StrOutputParser()
            reference = [
                {"qid": q["qid"], "answer": q.get("answer", "")} for q in questions
            ]
            checked_raw = check_chain.invoke(
                {
                    "questions": questions,
                    "answers": answers,
                    "reference": reference,
                    "graded": data,
                }
            )
            checked_text = _extract_json_text(checked_raw)
            try:
                checked = json.loads(checked_text)
                if isinstance(checked, list):
                    return checked, raw
            except json.JSONDecodeError:
                pass
            return data, raw
    except json.JSONDecodeError:
        pass

    # 记录原始输出，便于排查
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "llm_grade_raw.txt"), "w", encoding="utf-8") as f:
        f.write(raw)
    return [], raw
