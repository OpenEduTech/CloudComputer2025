import pytest
from unittest.mock import Mock, patch
from models.answer_evaluator import AnswerEvaluator
from models import Question, EvaluationResult
from models.config import Config


class TestAnswerEvaluator:
    """AnswerEvaluator 单元测试"""
    
    @pytest.fixture
    def config(self):
        """创建配置"""
        config = Mock(spec=Config)
        config.OPENAI_API_KEY = "test-key"
        config.OPENAI_BASE_URL = "https://api.openai.com/v1"
        config.OPENAI_MODEL = "gpt-3.5-turbo"
        return config
    
    @pytest.fixture
    def evaluator(self, config):
        """创建评估器"""
        with patch('models.answer_evaluator.OpenAI'):
            return AnswerEvaluator(config)
    
    @pytest.fixture
    def sample_question(self):
        """创建示例题目"""
        return Question(
            question_id="q1",
            question_type="multiple_choice",
            content="什么是过拟合？",
            options=["A. 模型过于复杂", "B. 数据不足", "C. 学习率过高", "D. 特征过多"],
            correct_answer="A. 模型过于复杂",
            explanation="过拟合发生在模型过于复杂时，在训练数据上表现好，但新数据表现差。",
            difficulty="medium",
            source_chunks=["chunk1"],
            tags=["overfitting", "model_complexity"],
            metadata={"source": "textbook"}
        )
    
    def test_evaluator_initialization(self, evaluator, config):
        """测试：评估器正确初始化"""
        assert evaluator is not None
        assert evaluator.config == config
    
    def test_evaluate_correct_answer(self, evaluator, sample_question):
        """测试：正确答案评估"""
        user_answer = "A. 模型过于复杂"
        
        with patch.object(evaluator.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content='{"is_correct": true, "score": 100}'))]
            mock_create.return_value = mock_response
            
            result = evaluator.evaluate_answer(sample_question, user_answer)
            
            assert isinstance(result, EvaluationResult)
            assert hasattr(result, 'is_correct')
            assert hasattr(result, 'score')
            assert hasattr(result, 'detailed_explanation')
    
    def test_evaluate_wrong_answer(self, evaluator, sample_question):
        """测试：错误答案评估"""
        user_answer = "B. 数据不足"
        
        with patch.object(evaluator.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content='{"is_correct": false, "score": 0}'))]
            mock_create.return_value = mock_response
            
            result = evaluator.evaluate_answer(sample_question, user_answer)
            
            assert isinstance(result, EvaluationResult)
            assert hasattr(result, 'is_correct')
            assert hasattr(result, 'mistakes')
    
    def test_evaluation_result_fields(self, evaluator, sample_question):
        """测试：评估结果包含所有必要字段"""
        user_answer = "A. 模型过于复杂"
        
        with patch.object(evaluator.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(
                content='{"is_correct": true, "score": 100, "mistakes": []}'
            ))]
            mock_create.return_value = mock_response
            
            result = evaluator.evaluate_answer(sample_question, user_answer)
            
            required_fields = [
                'is_correct', 'score', 'feedback', 'detailed_explanation',
                'suggested_improvement', 'confidence_score', 'mistakes'
            ]
            for field in required_fields:
                assert hasattr(result, field), f"缺少字段: {field}"
    
    def test_score_range(self, evaluator, sample_question):
        """测试：分数在有效范围内（0-100）"""
        user_answer = "A. 模型过于复杂"
        
        with patch.object(evaluator.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content='{"is_correct": true, "score": 85}'))]
            mock_create.return_value = mock_response
            
            result = evaluator.evaluate_answer(sample_question, user_answer)
            
            assert 0 <= result.score <= 100, "分数必须在 0-100 之间"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
