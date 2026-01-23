import json
from typing import Dict, List, Any, Tuple
from openai import OpenAI
from models import Question, EvaluationResult

class AnswerEvaluator:
    """智能评估用户答案，使用Prometheus模式提高公平性"""
    
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        )
    
    def evaluate_answer(
        self, 
        question: Question, 
        user_answer: str,
        user_history: Dict = None
    ) -> EvaluationResult:
        """评估用户答案"""
        
        if question.question_type == "multiple_choice":
            return self._evaluate_multiple_choice(question, user_answer)
        elif question.question_type == "true_false":
            return self._evaluate_true_false(question, user_answer)
        elif question.question_type == "short_answer":
            return self._evaluate_short_answer(question, user_answer, user_history)
        else:
            raise ValueError(f"Unknown question type: {question.question_type}")
    
    def _evaluate_multiple_choice(
        self, 
        question: Question, 
        user_answer: str
    ) -> EvaluationResult:
        """评估选择题答案"""
        # 直接比较答案
        is_correct = (user_answer.strip().lower() == 
                     question.correct_answer.strip().lower())
        
        score = 100 if is_correct else 0
        
        feedback = "回答正确！" if is_correct else "回答错误。"
        
        if not is_correct:
            mistakes = [f"选择了错误选项: {user_answer}"]
        else:
            mistakes = []
        
        return EvaluationResult(
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            detailed_explanation=question.explanation,
            suggested_improvement=self._get_improvement_suggestion(
                question, user_answer, is_correct
            ),
            confidence_score=1.0,
            mistakes=mistakes
        )
    
    def _evaluate_true_false(
        self, 
        question: Question, 
        user_answer: str
    ) -> EvaluationResult:
        """评估真假题答案"""
        # 规范化答案（处理各种格式：T/F, True/False, 对/错, 是/否等）
        normalized_answer = user_answer.strip().lower()
        normalized_correct = question.correct_answer.strip().lower()
        
        # 处理多种真假值格式
        true_variations = ["true", "t", "是", "对", "yes", "y"]
        false_variations = ["false", "f", "否", "错", "no", "n"]
        
        # 规范化用户答案
        if normalized_answer in true_variations:
            user_choice = "true"
        elif normalized_answer in false_variations:
            user_choice = "false"
        else:
            user_choice = normalized_answer
        
        # 规范化正确答案
        if normalized_correct in true_variations:
            correct_choice = "true"
        elif normalized_correct in false_variations:
            correct_choice = "false"
        else:
            correct_choice = normalized_correct
        
        is_correct = (user_choice == correct_choice)
        score = 100 if is_correct else 0
        feedback = "回答正确！" if is_correct else "回答错误。"
        
        if not is_correct:
            mistakes = [f"选择了错误答案: {user_answer}，正确答案是: {question.correct_answer}"]
        else:
            mistakes = []
        
        return EvaluationResult(
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            detailed_explanation=question.explanation,
            suggested_improvement=self._get_improvement_suggestion(
                question, user_answer, is_correct
            ),
            confidence_score=1.0,
            mistakes=mistakes
        )
    
    def _evaluate_short_answer(
        self, 
        question: Question,
        user_answer: str,
        user_history: Dict = None
    ) -> EvaluationResult:
        """使用Prometheus模式评估简答题"""
        
        prompt = self._build_prometheus_prompt(question, user_answer)
        
        response = self.client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        try:
            evaluation = json.loads(response.choices[0].message.content)
            
            # 验证评估结果
            self._validate_evaluation(evaluation)
            
            return EvaluationResult(
                is_correct=evaluation.get("is_correct", False),
                score=evaluation.get("score", 0),
                feedback=evaluation.get("feedback", ""),
                detailed_explanation=evaluation.get("detailed_explanation", ""),
                suggested_improvement=evaluation.get("suggested_improvement", ""),
                confidence_score=evaluation.get("confidence_score", 0.8),
                mistakes=evaluation.get("mistakes", [])
            )
        except Exception as e:
            # 如果评估失败，使用备用方案
            return self._fallback_evaluation(question, user_answer)
    
    def _build_prometheus_prompt(self, question: Question, user_answer: str) -> str:
        """构建Prometheus评估提示词"""
        return f"""你是一个公平、客观的评估专家。请评估以下答案：

        问题：{question.content}
        
        参考答案：{question.correct_answer}
        
        评分标准：{json.dumps(question.metadata.get('scoring_criteria', []), ensure_ascii=False)}
        
        用户答案：{user_answer}
        
        请按照以下步骤进行（CoT推理）：
        1. 分析用户答案是否涵盖了参考答案的关键要点
        2. 检查是否有事实性错误
        3. 评估答案的完整性和准确性
        4. 给出具体的改进建议
        
        请以JSON格式返回评估结果：
        {{
            "is_correct": true/false,
            "score": 0-100,
            "feedback": "总体反馈",
            "detailed_explanation": "详细解释",
            "suggested_improvement": "改进建议",
            "confidence_score": 0-1,
            "mistakes": ["错误点1", "错误点2"]
        }}
        
        确保评估公平，避免过于严格或宽松。"""
    
    def _validate_evaluation(self, evaluation: Dict) -> None:
        """验证评估结果的合理性"""
        required_fields = ["score", "feedback", "detailed_explanation"]
        for field in required_fields:
            if field not in evaluation:
                raise ValueError(f"Missing required field: {field}")
        
        if not 0 <= evaluation["score"] <= 100:
            raise ValueError(f"Invalid score: {evaluation['score']}")
    
    def _fallback_evaluation(self, question: Question, user_answer: str) -> EvaluationResult:
        """备用评估方案"""
        # 简单的语义相似度评估
        # 这里可以加入embedding相似度计算
        return EvaluationResult(
            is_correct=False,
            score=50,  # 默认中等分数
            feedback="自动评估系统暂时不可用",
            detailed_explanation=question.explanation,
            suggested_improvement="请参考答案进行对比学习",
            confidence_score=0.5,
            mistakes=["评估系统临时故障"]
        )
    
    def _get_improvement_suggestion(
        self, 
        question: Question, 
        user_answer: str, 
        is_correct: bool
    ) -> str:
        """获取个性化改进建议"""
        if is_correct:
            return "回答得很好！可以尝试挑战更高难度的题目。"
        else:
            return f"建议重点复习相关概念：{', '.join(question.tags[:3])}"