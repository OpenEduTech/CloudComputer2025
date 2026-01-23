from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from openai import OpenAI

from app.tutor_runtime.gate import run_with_checker
from app.tutor_runtime.tutor_check import TutorCheck
from app.tutor_runtime.utils import make_jsonable


KIMI_API_KEY = os.getenv("MOONSHOT_API_KEY")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")


def _call_kimi(prompt: str) -> str:
    if not KIMI_API_KEY:
        raise RuntimeError("MOONSHOT_API_KEY is required for tutor")
    client = OpenAI(api_key=KIMI_API_KEY, base_url="https://api.moonshot.cn/v1")
    resp = client.chat.completions.create(
        model=KIMI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful tutor who gives ONE step at a time. Output JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def _build_prompt(session: Dict[str, Any], message: str, hint_level: str) -> str:
    """Build a strict prompt that enforces the hint ladder."""

    # MongoDB documents may contain datetime/ObjectId which are not JSON serializable.
    diagnosis = make_jsonable(session.get("diagnosis") or {})
    question_meta = make_jsonable(session.get("question") or {})
    if hint_level.upper() != "FINAL" and isinstance(question_meta, dict):
        question_meta.pop("reference_analysis", None)
    history = make_jsonable(session.get("history") or [])
    # Keep only last 10 messages
    history = history[-10:]

    ladder_rules = {
        "L0": "指出可能忽略的条件/定义，不给答案；用1个提示+1个反问引导学生检查。",
        "L1": "给一个关键概念提示，并让学生用自己的话复述/应用；不泄露最终答案。",
        "L2": "给一步推导/一步判断（只一步），让学生继续；不泄露最终答案。",
        "FINAL": "学生明确放弃或轮次超限：给完整讲解和最终答案（允许直接给答案）。",
    }

    schema = {
        "hint_level": hint_level,
        "question": "string (ask ONE question to the student)",
        "hint": "string (give ONE hint; be concise)",
        "done": "boolean (true only if FINAL and you have provided full solution)",
        "final_answer": "string (ONLY when hint_level is FINAL)",
        "worked_solution": "string (ONLY when hint_level is FINAL; can be short)",
    }

    ref_line = ""
    if hint_level.upper() == "FINAL":
        ref_line = f"reference_answer(仅供导师内部对齐，FINAL前禁止泄露): {session.get('correct_answer', '')}\n"

    return (
        "你是学生的引导式导师(Tutor)。你的任务是‘一轮只给一步’，使用提示阶梯(Hint ladder)。\n"
        "严格要求：\n"
        "- 只输出 JSON 对象，不要 markdown，不要多余解释。\n"
        "- hint_level != FINAL 时，禁止出现‘正确答案/答案是/选项X’等任何泄露最终答案的内容。\n"
        "- 必须引用学生的作答或本轮提问中的关键词，保证回复与学生输入相关。\n"
        "- 选择题不要使用选项字母，尽量用选项内容或概念进行引导。\n"
        "- 每轮只能给一步：1个hint + 1个question。\n"
        "\n"
        f"本轮 hint_level = {hint_level}\n"
        f"本轮规则：{ladder_rules.get(hint_level, ladder_rules['L0'])}\n\n"
        "输出 JSON 结构（字段名必须一致）：\n"
        f"{json.dumps(schema, ensure_ascii=False)}\n\n"
        "=== 题目信息 ===\n"
        f"stem: {session.get('stem','')}\n"
        f"student_answer: {session.get('student_answer','')}\n"
        f"question_meta(type/options/knowledge_points/reference_analysis): {json.dumps(question_meta, ensure_ascii=False)}\n"
        f"{ref_line}"
        f"diagnosis(missing_points/error_tags/weak_node_ids): {json.dumps(diagnosis, ensure_ascii=False)}\n\n"
        "=== 对话历史(最近10条) ===\n"
        f"{json.dumps(history, ensure_ascii=False)}\n\n"
        "=== 学生本轮输入 ===\n"
        f"{message}\n"
    )


def run_tutor_turn(session: Dict[str, Any], message: str, hint_level: str) -> Dict[str, Any]:
    """Run one tutor turn with retry gate + TutorCheck.

    Important: TutorCheck may fail repeatedly if the LLM keeps leaking answers.
    For demo stability we MUST NOT crash the whole request; instead we fall back
    to a safe, non-answer-revealing hint.
    """

    prompt = _build_prompt(session=session, message=message, hint_level=hint_level)
    checker = TutorCheck()

    try:
        _raw, parsed = run_with_checker(
            llm_call=_call_kimi,
            prompt=prompt,
            checker=checker,
            context={"hint_level": hint_level, "correct_answer": session.get("correct_answer")},
            max_retries=2,
        )
    except Exception as e:
        # Safe fallback: never reveal final answer when not FINAL.
        hl = (hint_level or "L0").upper()
        diag = session.get("diagnosis") or {}
        missing = (diag.get("missing_points") or []) if isinstance(diag, dict) else []
        tags = (diag.get("error_tags") or []) if isinstance(diag, dict) else []

        if hl == "L1":
            hint = "我们先抓住一个关键概念：" + (missing[0] if missing else (tags[0] if tags else "题目中的核心定义/条件")) + "。请你用自己的话解释它，并说明它在这题里怎么用。"
            question = "你能先把这个概念/条件写成一句话（或公式）吗？"
        elif hl == "L2":
            hint = "只做一步：把题目已知条件按顺序列出，然后选其中一个条件代入你正在用的公式/定义，看看能推出什么中间量。"
            question = "你现在列出的第一个已知条件是什么？用它你能推出哪个中间结果？"
        elif hl == "FINAL":
            # FINAL 允许给答案，但如果模型不可用也给一个可交付的讲解骨架
            hint = "我来给出完整解题思路：先列条件→选用定义/公式→逐步推出中间量→得到结论。"
            question = "（已结束）"
        else:
            hint = "先别急着算。请回到题干，把‘已知条件/关键词/限制’逐条圈出来，对照你的解法看看你是否遗漏了某个条件或定义。"
            question = "你觉得你最可能漏掉的是哪一个条件/定义？把它写出来。"

        return {
            "hint_level": hint_level,
            "question": question,
            "hint": hint,
            "done": bool(hl == "FINAL"),
            "error": str(e),
        }

    # run_with_checker returns parsed dict when PASS
    if not isinstance(parsed, dict):
        # defensive fallback
        return {
            "hint_level": hint_level,
            "question": "你能指出这题里你最不确定的那个条件/定义是什么吗？",
            "hint": "先把题目的已知条件列出来，再对照你用到的公式/定义，看看缺了哪一步。",
            "done": False,
        }

    # Ensure required keys exist
    parsed.setdefault("hint_level", hint_level)
    parsed.setdefault(
        "done",
        bool(hint_level.upper() == "FINAL" and (parsed.get("final_answer") or parsed.get("worked_solution"))),
    )
    return parsed
