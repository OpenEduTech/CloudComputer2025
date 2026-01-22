"""
小灶纠偏Agent
"""
from openai import AsyncOpenAI
import logging
from typing import Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class RemediationAgent:
    """个性化纠偏Agent"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.deepseek_api_base
        )
        self.model = settings.DEEPSEEK_MODEL

    async def generate_remediation(
        self,
        question: str,
        correct_answer: str,
        user_answer: str,
        error_type: str | None,
        user_profile: str | None,
        focus_topic: str | None
    ) -> Dict[str, Any]:
        """生成个性化纠偏内容"""
        prompt = self._build_prompt(
            question, correct_answer, user_answer, error_type, user_profile, focus_topic
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个擅长纠偏教学的资深助教。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=1800,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        parsed = self._parse_response(content)
        parsed["markdown"] = self._to_markdown(parsed)
        return parsed

    def _build_prompt(
        self,
        question: str,
        correct_answer: str,
        user_answer: str,
        error_type: str | None,
        user_profile: str | None,
        focus_topic: str | None
    ) -> str:
        profile = user_profile or "无"
        err = error_type or "未知"
        topic = focus_topic or "无"

        return f"""你是教学助教。请进行个性化纠偏，遵循“精讲-对比-再练-迁移”的结构。

题目：{question}
正确答案：{correct_answer}
学生答案：{user_answer}
错误类型：{err}
知识点：{topic}
用户画像：{profile}

要求：
1) 精讲：用不同于PPT的方式重新讲解
2) 对比：指出正确理解 vs 错误理解
3) 再练：给1道针对该错因的练习题（含标准答案与解析）
4) 迁移：给1道相似但不同题（含标准答案与解析）
5) 输出JSON

JSON格式（仅输出JSON，不要输出额外文字）：
{{
  "explain": "精讲内容",
  "contrast": "正确 vs 错误理解对比",
  "practice": {{"question": "题目", "answer": "答案", "explanation": "解析"}},
  "transfer": {{"question": "题目", "answer": "答案", "explanation": "解析"}},
  "tips": ["建议1", "建议2"]
}}
"""

    def _parse_response(self, response: str) -> Dict[str, Any]:
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                import json
                data = json.loads(response[start_idx:end_idx])
                return data
        except Exception as e:
            logger.warning(f"纠偏结果解析失败: {e}")

        # 降级返回
        return {
            "explain": response,
            "contrast": "",
            "practice": {"question": "", "answer": "", "explanation": ""},
            "transfer": {"question": "", "answer": "", "explanation": ""},
            "tips": []
        }

    def _to_markdown(self, data: Dict[str, Any]) -> str:
        """将纠偏内容转为Markdown"""
        explain = data.get("explain", "")
        contrast = data.get("contrast", "")
        practice = data.get("practice", {}) or {}
        transfer = data.get("transfer", {}) or {}
        tips = data.get("tips", []) or []

        tips_md = "\n".join(f"- {t}" for t in tips) if tips else "- 无"

        return (
            "# 个性化小灶\n\n"
            "## 精讲\n"
            f"{explain}\n\n"
            "## 对比\n"
            f"{contrast}\n\n"
            "## 再练\n"
            f"**题目**：{practice.get('question','')}\n\n"
            f"**答案**：{practice.get('answer','')}\n\n"
            f"**解析**：{practice.get('explanation','')}\n\n"
            "## 迁移\n"
            f"**题目**：{transfer.get('question','')}\n\n"
            f"**答案**：{transfer.get('answer','')}\n\n"
            f"**解析**：{transfer.get('explanation','')}\n\n"
            "## 建议\n"
            f"{tips_md}\n"
        )
