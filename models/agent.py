from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from models import Question, EvaluationResult

class LLMAgent:
    """学习评估和巩固智能体"""
    
    def __init__(self, config):
        self.config = config
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化各个组件"""
        from models.data_processor import DataProcessor
        from models.question_generator import QuestionGenerator
        from models.answer_evaluator import AnswerEvaluator
        from models.weakness_analyzer import WeaknessAnalyzer
        from models.mongodb_client import MongoDBClient
        
        # 初始化组件
        self.data_processor = DataProcessor(self.config)
        self.question_generator = QuestionGenerator(self.config)
        self.answer_evaluator = AnswerEvaluator(self.config)
        self.mongo_client = MongoDBClient(self.config)
        self.weakness_analyzer = WeaknessAnalyzer(self.mongo_client)
        
        # 缓存
        self.question_cache = {}
        self.user_sessions = {}
    
    def process_material(self, material_input: Any) -> List[Any]:
        """处理学习资料"""
        if isinstance(material_input, dict) and material_input.get("type") == "pdf":
            chunks = self.data_processor.process_input(
                material_input["path"], 
                input_type="pdf"
            )
        else:
            # 假设是文本
            chunks = self.data_processor.process_input(str(material_input))
        
        # 提取关键概念（只提取一次，后续复用）
        key_concepts = self.data_processor.extract_key_concepts(chunks)
        
        # 缓存处理结果
        session_id = f"session_{datetime.now().timestamp()}"
        self.user_sessions[session_id] = {
            "chunks": chunks,
            "key_concepts": key_concepts,
            "key_concepts": key_concepts,
            "timestamp": datetime.now()
        }
        
        return chunks
    
    def generate_questions(
        self, 
        chunks: List[Any],
        num_questions: int = 5,
        question_types: List[str] = None,
        difficulty_mix: str = "adaptive"
    ) -> List[Question]:
        """生成评估题目"""
        
        # 获取最新的session
        latest_session_key = sorted(self.user_sessions.keys())[-1] if self.user_sessions else None
        latest_concepts = self.user_sessions.get(latest_session_key, {}).get("key_concepts") if latest_session_key else None
        
        # 如果没有指定题目类型，根据难度混合设置调整参数
        if question_types is None:
            if difficulty_mix == "简单为主":
                question_types = ["multiple_choice"]  # 选择题为主
                difficulty_bias = "easy"
            elif difficulty_mix == "挑战难度":
                question_types = ["short_answer"]  # 简答题为主
                difficulty_bias = "hard"
            else:
                question_types = list(self.config.QUESTION_TYPES)
                difficulty_bias = None
        
        questions = self.question_generator.generate_questions(
            chunks,
            num_questions=num_questions,
            question_types=question_types,
            pre_extracted_concepts=latest_concepts
        )
        
        # 缓存问题
        for q in questions:
            self.question_cache[q.question_id] = q
        
        return questions
    
    def generate_questions_stream(
        self,
        chunks: List[Any],
        num_questions: int = 5,
        question_types: List[str] = None,
        difficulty_mix: str = "adaptive",
        on_question_start: callable = None,
        on_question_chunk: callable = None,
        on_question_complete: callable = None
    ) -> List[Question]:
        """流式生成评估题目"""
        
        # 获取最新的session
        latest_session_key = sorted(self.user_sessions.keys())[-1] if self.user_sessions else None
        latest_concepts = self.user_sessions.get(latest_session_key, {}).get("key_concepts") if latest_session_key else None
        
        # 如果没有指定题目类型，根据难度混合设置调整参数
        if question_types is None:
            if difficulty_mix == "简单为主":
                question_types = ["multiple_choice"]
                difficulty_bias = "easy"
            elif difficulty_mix == "挑战难度":
                question_types = ["short_answer"]
                difficulty_bias = "hard"
            else:
                question_types = list(self.config.QUESTION_TYPES)
                difficulty_bias = None
        
        questions = self.question_generator.generate_questions_stream(
            chunks,
            num_questions=num_questions,
            question_types=question_types,
            pre_extracted_concepts=latest_concepts,
            on_question_start=on_question_start,
            on_question_chunk=on_question_chunk,
            on_question_complete=on_question_complete
        )
        
        # 缓存问题
        for q in questions:
            self.question_cache[q.question_id] = q
        
        return questions
    
    def evaluate_answer(
        self, 
        question: Question, 
        user_answer: str,
        user_history: Optional[Dict] = None
    ) -> EvaluationResult:
        """评估用户答案"""
        return self.answer_evaluator.evaluate_answer(
            question, 
            user_answer, 
            user_history
        )
    
    def save_performance(
        self, 
        user_id: str, 
        question: Question,
        evaluation: EvaluationResult,
        user_answer: str
    ):
        """保存用户表现"""
        return self.mongo_client.save_user_performance(
            user_id, 
            question,
            evaluation,
            user_answer
        )
    
    def get_wrong_questions(
        self, 
        user_id: str, 
        limit: int = 20
    ) -> List[Dict]:
        """获取用户错题"""
        return self.mongo_client.get_wrong_questions(user_id, limit)
    
    def get_user_statistics(self, user_id: str) -> Dict:
        """获取用户统计"""
        return self.mongo_client.get_user_statistics(user_id)
    
    def analyze_weaknesses(self, user_id: str) -> Dict:
        """分析用户弱点"""
        return self.weakness_analyzer.analyze_user_weaknesses(user_id)
    
    def generate_targeted_practice(
        self, 
        user_id: str, 
        chunks: List[Any]
    ) -> List[Question]:
        """生成针对性练习"""
        analysis = self.analyze_weaknesses(user_id)
        
        if not analysis.get("weaknesses"):
            # 如果没有弱点，生成综合练习
            return self.generate_questions(chunks, num_questions=3)
        
        # 针对弱点生成题目
        weaknesses = analysis["weaknesses"]
        return self.weakness_analyzer.generate_targeted_questions(
            weaknesses,
            self.question_cache.values()
        )
    
    def get_study_plan(self, user_id: str) -> Dict:
        """获取学习计划"""
        analysis = self.analyze_weaknesses(user_id)
        
        if not analysis.get("weaknesses"):
            return {"status": "no_weaknesses", "message": "暂无需要改进的方面"}
        
        return self.weakness_analyzer.create_study_plan(analysis["weaknesses"])
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'mongo_client'):
            self.mongo_client.close()