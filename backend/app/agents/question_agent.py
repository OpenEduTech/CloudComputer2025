"""
出题判卷Agent
"""
from openai import AsyncOpenAI
import logging
import json
import uuid
from typing import List, Dict, Any
import math

from app.core.config import settings
from app.models.schemas import (
    Question, QuestionType, DifficultyLevel,
    QuestionOption, AnswerEvaluation
)
from app.core.llm_validation import (
    validate_questions_response,
    validate_evaluation_response
)

logger = logging.getLogger(__name__)


class QuestionGenerationAgent:
    """出题Agent"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.deepseek_api_base
        )
        self.model = settings.DEEPSEEK_MODEL
    
    async def generate_questions(
        self,
        content: str,
        num_questions: int = 5,
        question_types: List[QuestionType] = None,
        difficulty_levels: List[DifficultyLevel] = None,
        strict_context: bool = True,
        context_hint: str | None = None
    ) -> List[Question]:
        """
        生成题目
        
        Args:
            content: 学习内容
            num_questions: 题目数量
            question_types: 题目类型列表
            difficulty_levels: 难度等级列表
        """
        if question_types is None:
            question_types = [QuestionType.CHOICE]
        if difficulty_levels is None:
            difficulty_levels = [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD]
        
        try:
            prompt = self._build_generation_prompt(
                content, num_questions, question_types, difficulty_levels, strict_context, context_hint
            )
            
            response = await self._call_llm(prompt)
            questions = self._parse_questions(response, question_types)

            llm_validation = None
            if settings.LLM_VALIDATION_ENABLED:
                llm_validation = validate_questions_response(
                    response,
                    [q.model_dump() for q in questions]
                )
            
            # 校验层：确保题目质量
            validated_questions = self._validate_questions(questions)
            
            return {
                "questions": validated_questions[:num_questions],
                "llm_validation": llm_validation
            }
            
        except Exception as e:
            logger.error(f"生成题目失败: {e}", exc_info=True)
            raise
    
    def _build_generation_prompt(
        self,
        content: str,
        num_questions: int,
        question_types: List[QuestionType],
        difficulty_levels: List[DifficultyLevel],
        strict_context: bool,
        context_hint: str | None
    ) -> str:
        """构建出题提示词"""
        
        types_str = "、".join([qt.value for qt in question_types])
        levels_str = "、".join([dl.value for dl in difficulty_levels])
        
        guard = "必须严格基于以下上下文出题，禁止引入上下文之外的新知识" if strict_context else "尽量基于上下文出题"
        hint = f"\n\n知识点定位提示：{context_hint}" if context_hint else ""

        prompt = f"""你是一个专业的教育评估专家，擅长根据学习材料出题。

学习内容：
{content}

    约束：
    {guard}{hint}

任务：基于以上内容，生成{num_questions}道高质量的题目。

要求：
1. 题目类型：{types_str}
2. 难度分布：{levels_str}（均匀分布）
3. 题目应覆盖核心知识点
4. 每道题都要有详细解析
5. 选择题必须有4个选项（A、B、C、D）
6. 确保答案准确无误

请按以下JSON格式返回（仅输出JSON，不要输出额外文字）：
{{
    "questions": [
        {{
            "type": "choice/short_answer/true_false",
            "difficulty": "easy/medium/hard",
            "content": "题目内容",
            "options": [
                {{"key": "A", "value": "选项A"}},
                {{"key": "B", "value": "选项B"}},
                {{"key": "C", "value": "选项C"}},
                {{"key": "D", "value": "选项D"}}
            ],
            "correct_answer": "正确答案",
            "explanation": "详细解析",
            "tags": ["标签1", "标签2"]
        }}
    ]
}}

出题策略：
1. 识别内容的核心概念和关键知识点
2. 根据难度梯度设计题目（从易到难）
3. 确保题目有区分度
4. 提供详尽的解析帮助学习

请开始："""
        return prompt
    
    async def _call_llm(self, prompt: str, retries: int = 0) -> str:
        """调用LLM"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是专业的教育评估专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,  # 稍高温度以增加题目多样性
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return content
            
        except Exception as e:
            if retries < settings.MAX_RETRIES:
                logger.warning(f"LLM调用失败，重试 {retries + 1}/{settings.MAX_RETRIES}")
                return await self._call_llm(prompt, retries + 1)
            else:
                raise
    
    def _parse_questions(self, response: str, question_types: List[QuestionType]) -> List[Question]:
        """解析题目"""
        try:
            # 提取JSON
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx <= start_idx:
                raise ValueError("无法从响应中提取JSON")
            
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            questions = []
            for q_data in data.get("questions", []):
                try:
                    question = Question(
                        question_id=str(uuid.uuid4()),
                        question_type=QuestionType(q_data.get("type", "choice")),
                        difficulty=DifficultyLevel(q_data.get("difficulty", "medium")),
                        content=q_data.get("content", ""),
                        options=[
                            QuestionOption(**opt) for opt in q_data.get("options", [])
                        ] if q_data.get("options") else None,
                        correct_answer=q_data.get("correct_answer", ""),
                        explanation=q_data.get("explanation", ""),
                        tags=q_data.get("tags", [])
                    )
                    questions.append(question)
                except Exception as e:
                    logger.warning(f"解析单个题目失败: {e}")
                    continue
            
            return questions
            
        except Exception as e:
            logger.error(f"解析题目失败: {e}")
            return []
    
    def _validate_questions(self, questions: List[Question]) -> List[Question]:
        """校验题目质量"""
        validated = []
        
        for q in questions:
            # 基本校验
            if not q.content or len(q.content) < 10:
                logger.warning(f"题目内容过短，跳过: {q.question_id}")
                continue
            
            if not q.correct_answer:
                logger.warning(f"缺少正确答案，跳过: {q.question_id}")
                continue
            
            # 选择题特殊校验
            if q.question_type == QuestionType.CHOICE:
                if not q.options or len(q.options) < 2:
                    logger.warning(f"选择题选项不足，跳过: {q.question_id}")
                    continue
                
                # 检查答案是否在选项中
                option_keys = [opt.key for opt in q.options]
                if q.correct_answer not in option_keys:
                    logger.warning(f"答案不在选项中，跳过: {q.question_id}")
                    continue
            
            validated.append(q)
        
        return validated


class AnswerEvaluationAgent:
    """判卷Agent"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.deepseek_api_base
        )
        self.model = settings.DEEPSEEK_MODEL
    
    async def evaluate_answer(
        self,
        question: Question,
        user_answer: str
    ) -> AnswerEvaluation:
        """
        评估答案
        
        Args:
            question: 题目
            user_answer: 用户答案
        """
        try:
            # 选择题：直接比对
            if question.question_type == QuestionType.CHOICE:
                return self._evaluate_choice(question, user_answer)
            
            # 主观题：使用LLM评分
            elif question.question_type in [QuestionType.SHORT_ANSWER, QuestionType.TRUE_FALSE]:
                return await self._evaluate_subjective(question, user_answer)
            
        except Exception as e:
            logger.error(f"评估答案失败: {e}", exc_info=True)
            raise
    
    def _evaluate_choice(self, question: Question, user_answer: str) -> AnswerEvaluation:
        """评估选择题"""
        is_correct = user_answer.upper().strip() == question.correct_answer.upper().strip()
        score = 100.0 if is_correct else 0.0
        
        feedback = f"{'✓ 回答正确！' if is_correct else '✗ 回答错误'}\n\n"
        feedback += f"正确答案：{question.correct_answer}\n\n"
        feedback += f"解析：{question.explanation}"
        
        suggestions = []
        if not is_correct:
            suggestions = [
                f"请重点复习：{question.explanation}",
                "建议查看相关章节内容",
                "可以尝试相似题目巩固"
            ]
        
        return AnswerEvaluation(
            question_id=question.question_id,
            is_correct=is_correct,
            score=score,
            user_answer=user_answer,
            correct_answer=question.correct_answer,
            detailed_feedback=feedback,
            improvement_suggestions=suggestions,
            semantic_similarity=1.0 if is_correct else 0.0,
            error_type=None
        )
    
    async def _evaluate_subjective(self, question: Question, user_answer: str) -> AnswerEvaluation:
        """评估主观题（使用LLM + Embedding相似度）"""
        # 1) 语义相似度检测（答非所问判断）
        similarity = await self._compute_similarity(user_answer, question.correct_answer)

        # 2) LLM评分与错误类型分类
        prompt = self._build_evaluation_prompt(question, user_answer, similarity)
        response = await self._call_llm(prompt)
        evaluation = self._parse_evaluation(response, question, user_answer, similarity)

        if settings.LLM_VALIDATION_ENABLED:
            try:
                evaluation.llm_validation = validate_evaluation_response(
                    response,
                    evaluation.model_dump()
                )
            except Exception as e:
                logger.warning(f"LLM校验失败: {e}")

        # 3) 低相似度兜底
        if similarity is not None and similarity < settings.ANSWER_SIMILARITY_THRESHOLD:
            evaluation.is_correct = False
            evaluation.error_type = evaluation.error_type or "答非所问"
            evaluation.detailed_feedback += "\n\n⚠️ 语义相似度较低，疑似答非所问。"

        return evaluation
    
    def _build_evaluation_prompt(self, question: Question, user_answer: str, similarity: float | None) -> str:
        """构建评估提示词（Prometheus方法 + 误差分类）"""
        sim_text = f"语义相似度(0~1)：{similarity:.3f}" if similarity is not None else "语义相似度：未知"
        prompt = f"""你是一个公正、严谨的阅卷专家。请对学生答案进行评分。

Prometheus评分法：
1) 明确评分量表（Rubric）
2) 对照参考答案与学生答案进行逐点比对
3) 输出可审计的评分摘要（不输出完整思维链）

题目：
{question.content}

标准答案：
{question.correct_answer}

学生答案：
{user_answer}

{sim_text}

评分标准（Rubric）：
1. 完整性（40%）：答案是否完整覆盖要点
2. 准确性（40%）：答案是否准确无误
3. 表达性（20%）：逻辑是否清晰

要求：
- 给出0-100分的分数
- 提供详细反馈
- 指出优点和不足
- 给出改进建议
- 保持客观公正，避免主观偏见
- 进行错误类型分类：概念错 / 计算错 / 理解偏差 / 答非所问 / 其他
- 给出推理对齐评分（0-100）与简述，不输出完整推理链

请按以下JSON格式返回（仅输出JSON，不要输出额外文字）：
{{
    "score": 85.0,
    "is_correct": true,
    "feedback": "详细反馈内容",
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "suggestions": ["建议1", "建议2"],
    "error_type": "概念错/计算错/理解偏差/答非所问/其他",
    "alignment_score": 78.0,
    "alignment_summary": "推理与标准答案部分一致，但遗漏关键步骤"
}}

请开始评分："""
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是公正的阅卷专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 低温度确保评分一致性
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content
    
    def _parse_evaluation(
        self,
        response: str,
        question: Question,
        user_answer: str,
        similarity: float | None
    ) -> AnswerEvaluation:
        """解析评估结果"""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            score = float(data.get("score", 0))
            is_correct = data.get("is_correct", score >= 60)
            
            feedback = data.get("feedback", "")
            if data.get("strengths"):
                feedback += "\n\n优点：\n" + "\n".join(f"• {s}" for s in data["strengths"])
            if data.get("weaknesses"):
                feedback += "\n\n不足：\n" + "\n".join(f"• {w}" for w in data["weaknesses"])
            
            suggestions = data.get("suggestions", [])
            
            return AnswerEvaluation(
                question_id=question.question_id,
                is_correct=is_correct,
                score=score,
                user_answer=user_answer,
                correct_answer=question.correct_answer,
                detailed_feedback=feedback,
                improvement_suggestions=suggestions,
                semantic_similarity=similarity,
                error_type=data.get("error_type"),
                alignment_score=data.get("alignment_score"),
                alignment_summary=data.get("alignment_summary")
            )
            
        except Exception as e:
            logger.error(f"解析评估结果失败: {e}")
            # 降级策略：简单判断
            return AnswerEvaluation(
                question_id=question.question_id,
                is_correct=False,
                score=0.0,
                user_answer=user_answer,
                correct_answer=question.correct_answer,
                detailed_feedback="评估系统暂时不可用，请稍后重试",
                improvement_suggestions=[],
                semantic_similarity=similarity,
                error_type="其他"
            )

    async def _compute_similarity(self, text_a: str, text_b: str) -> float | None:
        """使用Embedding计算语义相似度"""
        try:
            emb_a = await self._embed_text(text_a)
            emb_b = await self._embed_text(text_b)
            if not emb_a or not emb_b:
                return None

            return self._cosine_similarity(emb_a, emb_b)
        except Exception as e:
            logger.warning(f"相似度计算失败: {e}")
            return None

    async def _embed_text(self, text: str) -> List[float] | None:
        response = await self.client.embeddings.create(
            model=settings.DEEPSEEK_EMBEDDING_MODEL,
            input=text
        )
        if response.data and len(response.data) > 0:
            return response.data[0].embedding
        return None

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
