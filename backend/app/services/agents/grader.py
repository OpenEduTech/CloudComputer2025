from app.services.llm_factory import LLMFactory
from app.models.quiz import GradingResult, Question
from typing import Tuple
import json

class GraderAgent:
    def __init__(self):
        self.llm = LLMFactory.get_deepseek_llm()
        self.zhipu_client = LLMFactory.get_zhipu_client()

    async def _verify_grading(self, question: Question, user_answer: str, grading: GradingResult) -> Tuple[bool, str]:
        """
        验证评分结果是否合理，避免评分幻觉
        返回: (是否通过验证, 问题描述)
        """
        verification_prompt = f"""你是一位评分审核员，负责检查评分结果是否合理公正。

题目：{question.content}
题目类型：{question.type}
标准答案：{question.correct_answer}
学生答案：{user_answer}

评分结果：
- 是否正确：{grading.is_correct}
- 分数：{grading.score}
- 反馈：{grading.feedback}
- 错误类型：{grading.error_type}
- 分析：{grading.analysis}

请严格判断：
1. 评分结果（正确/错误）是否与学生答案和标准答案的对比一致？
2. 分数是否合理（正确应该接近1.0，错误应该接近0.0）？
3. 如果是计算题，数值是否准确对比？
4. 反馈和分析是否针对学生答案，而不是泛泛而谈？
5. 错误类型分类是否准确？
6. 是否存在明显的评分偏差或幻觉？

返回JSON格式：
{{
  "is_valid": true/false,
  "reason": "简要说明评分合理 或 指出评分问题"
}}

只返回JSON，不要其他文字。"""

        try:
            response = await self.llm.ainvoke(verification_prompt)
            content = response.content.strip()
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            return result.get("is_valid", True), result.get("reason", "未知原因")
        except Exception as e:
            print(f"⚠️  验证评分时出错: {e}")
            # 如果验证失败，默认通过
            return True, "验证系统异常，默认通过"

    async def grade_answer(self, question: Question, user_answer: str) -> GradingResult:
        """评分用户答案"""
        user_text_answer = user_answer
        
        # 检查是否是图片答案（Base64、URL或文件路径）
        answer_stripped = user_answer.strip()
        if (answer_stripped.startswith("data:image") or 
            answer_stripped.startswith("http") or 
            answer_stripped.startswith("uploaded/")):
            user_text_answer = self._describe_image(user_answer)
        
        # 第一次评分
        grading = await self._grade_text(question, user_text_answer)
        
        # Check layer: 验证评分结果
        print(f"🔍 验证评分结果（题目ID: {question.id[:8]}...）")
        is_valid, reason = await self._verify_grading(question, user_text_answer, grading)
        
        if is_valid:
            print(f"  ✓ 评分验证通过: {reason[:50]}...")
            return grading
        else:
            print(f"  ⚠️  评分验证失败: {reason}")
            print(f"  🔄 重新评分...")
            
            # 如果验证失败，重新评分一次（使用更严格的提示）
            grading_retry = await self._grade_text_strict(question, user_text_answer)
            
            # 再次验证
            is_valid_retry, reason_retry = await self._verify_grading(question, user_text_answer, grading_retry)
            
            if is_valid_retry:
                print(f"  ✓ 重新评分验证通过")
                return grading_retry
            else:
                print(f"  ⚠️  重新评分仍未通过，返回原评分")
                return grading

    def _describe_image(self, image_url: str) -> str:
        """使用智谱AI视觉模型识别图片中的答案"""
        try:
            response = self.zhipu_client.chat.completions.create(
                model="glm-4.6v", 
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": "请准确转录这张图片中的答案内容。如果是公式或文字，请完整写出。"}
                        ]
                    }
                ],
                thinking={
                    "type": "unenabled"
                }
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[图片识别错误: {e}]"

    async def _grade_text(self, question: Question, user_answer: str) -> GradingResult:
        """评分文本答案"""
        prompt = f"""你是一位严格的教师，请根据标准答案评判学生的答案。

题目：{question.content}
标准答案：{question.correct_answer}
学生答案：{user_answer}

请以JSON格式输出评分结果，包含以下字段：
- is_correct (布尔值，是否正确)
- score (0.0到1.0之间的分数)
- feedback (字符串，给学生的反馈)
- error_type (字符串："concept"概念错误、"logic"逻辑错误、"expression"表达不清，如果正确则为null)
- analysis (字符串，详细分析为什么正确或错误)

只返回JSON，不要有其他文字。"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content
            
            # JSON cleanup
            json_str = content.strip()
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_str)
            return GradingResult(question_id=question.id, **data)
        except Exception as e:
            print(f"评分出错: {e}")
            return GradingResult(
                question_id=question.id,
                is_correct=False,
                score=0.0,
                feedback="评分系统出错，请重试。",
                error_type="system",
                analysis=f"系统错误: {str(e)}"
            )

    async def _grade_text_strict(self, question: Question, user_answer: str) -> GradingResult:
        """更严格的评分（用于重试）"""
        prompt = f"""你是一位非常严格和公正的教师，请仔细对比学生答案和标准答案。

题目：{question.content}
题目类型：{question.type}
标准答案：{question.correct_answer}
学生答案：{user_answer}

评分要求：
1. 如果是计算题，必须精确对比数值和单位
2. 如果是概念题，要看学生是否理解核心概念，不要求完全一致
3. 如果是应用题，要看学生的思路和方法是否正确
4. 给出的反馈必须具体，指出学生答案的优点或问题
5. 分析必须基于学生的实际答案，不要泛泛而谈

请以JSON格式输出评分结果，包含以下字段：
- is_correct (布尔值，是否正确)
- score (0.0到1.0之间的分数，可以给部分分)
- feedback (字符串，给学生的具体反馈)
- error_type (字符串："concept"概念错误、"logic"逻辑错误、"expression"表达不清，如果正确则为null)
- analysis (字符串，详细分析学生答案的对错之处)

只返回JSON，不要有其他文字。"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content
            
            # JSON cleanup
            json_str = content.strip()
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_str)
            return GradingResult(question_id=question.id, **data)
        except Exception as e:
            print(f"严格评分出错: {e}")
            return GradingResult(
                question_id=question.id,
                is_correct=False,
                score=0.0,
                feedback="评分系统出错，请重试。",
                error_type="system",
                analysis=f"系统错误: {str(e)}"
            )

grader_agent = GraderAgent()
