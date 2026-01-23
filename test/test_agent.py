import pytest
from unittest.mock import Mock, patch, MagicMock
from models.agent import LLMAgent
from models import Chunk, Question, EvaluationResult
from models.config import Config


class TestAgent:
    """Agent 单元测试"""
    
    @pytest.fixture
    def config(self):
        """创建配置"""
        config = Mock(spec=Config)
        config.OPENAI_API_KEY = "test-key"
        config.OPENAI_BASE_URL = "https://api.openai.com/v1"
        config.OPENAI_MODEL = "gpt-3.5-turbo"
        config.QUESTION_TYPES = ["multiple_choice", "short_answer"]
        config.MONGODB_URI = "mongodb://localhost:27017"
        config.DB_NAME = "test_db"
        return config
    
    @pytest.fixture
    def sample_chunks(self):
        """创建示例分块"""
        return [
            Chunk(text="机器学习基础", metadata={"page": 1}),
            Chunk(text="监督学习方法", metadata={"page": 2}),
        ]
    
    @pytest.fixture
    def agent(self, config):
        """创建 Agent"""
        with patch.object(LLMAgent, '_initialize_components'):
            agent = LLMAgent(config)
            # 为 agent 添加必要的属性用于测试
            agent.data_processor = Mock()
            agent.question_generator = Mock()
            agent.answer_evaluator = Mock()
            agent.question_cache = {}
            agent.user_sessions = {}
            return agent
    
    def test_agent_initialization(self, agent, config):
        """测试：Agent 正确初始化"""
        assert agent is not None
        assert agent.config == config
    
    def test_process_material(self, agent, sample_chunks):
        """测试：处理学习资料"""
        agent.data_processor.process_input.return_value = sample_chunks
        agent.data_processor.extract_key_concepts.return_value = ["concept1", "concept2"]
        
        result = agent.process_material("测试资料文本")
        
        assert result is not None
        agent.data_processor.process_input.assert_called_once()
        agent.data_processor.extract_key_concepts.assert_called_once()
    
    def test_generate_questions(self, agent, sample_chunks):
        """测试：生成题目"""
        mock_question = Mock(spec=Question)
        mock_question.question_id = "q1"
        
        with patch.object(agent.question_generator, 'generate_questions') as mock_gen:
            mock_gen.return_value = [mock_question]
            
            questions = agent.generate_questions(sample_chunks, num_questions=1)
            
            assert len(questions) > 0
            mock_gen.assert_called_once()
    
    def test_generate_questions_stream(self, agent, sample_chunks):
        """测试：流式生成题目"""
        mock_question = Mock(spec=Question)
        mock_question.question_id = "q1"
        
        callbacks_called = {'start': False, 'complete': False}
        
        def on_start(curr, total):
            callbacks_called['start'] = True
        
        def on_complete(question):
            callbacks_called['complete'] = True
        
        with patch.object(agent.question_generator, 'generate_questions_stream') as mock_gen:
            mock_gen.return_value = [mock_question]
            
            questions = agent.generate_questions_stream(
                sample_chunks,
                num_questions=1,
                on_question_start=on_start,
                on_question_complete=on_complete
            )
            
            assert len(questions) > 0
            mock_gen.assert_called_once()
    
    def test_evaluate_answer(self, agent):
        """测试：评估答案"""
        mock_question = Mock(spec=Question)
        mock_question.content = "测试题目"
        mock_question.correct_answer = "正确答案"
        
        mock_result = Mock(spec=EvaluationResult)
        mock_result.is_correct = True
        mock_result.score = 100
        
        with patch.object(agent.answer_evaluator, 'evaluate_answer') as mock_eval:
            mock_eval.return_value = mock_result
            
            result = agent.evaluate_answer(mock_question, "正确答案")
            
            assert result.is_correct == True
            assert result.score == 100
    
    def test_question_caching(self, agent):
        """测试：题目缓存"""
        mock_question = Mock(spec=Question)
        mock_question.question_id = "q1"
        
        # 添加到缓存
        agent.question_cache["q1"] = mock_question
        
        # 验证缓存
        assert "q1" in agent.question_cache
        assert agent.question_cache["q1"] == mock_question


class TestAgentIntegration:
    """Agent 集成测试"""
    
    @pytest.fixture
    def config(self):
        """创建配置"""
        config = Mock(spec=Config)
        config.OPENAI_API_KEY = "test-key"
        config.OPENAI_BASE_URL = "https://api.openai.com/v1"
        config.OPENAI_MODEL = "gpt-3.5-turbo"
        config.QUESTION_TYPES = ["multiple_choice"]
        config.MONGODB_URI = "mongodb://localhost:27017"
        config.DB_NAME = "test_db"
        return config
    
    @pytest.fixture
    def agent(self, config):
        """创建 Agent"""
        with patch.object(LLMAgent, '_initialize_components'):
            agent = LLMAgent(config)
            agent.data_processor = Mock()
            agent.question_generator = Mock()
            agent.answer_evaluator = Mock()
            agent.question_cache = {}
            agent.user_sessions = {}
            return agent
    
    def test_session_management(self, agent):
        """测试：会话管理"""
        # 测试：处理资料会创建会话
        agent.data_processor.process_input.return_value = [
            Mock(spec=Chunk, text="sample", metadata={})
        ]
        agent.data_processor.extract_key_concepts.return_value = []
        
        result = agent.process_material("test material")
        
        # 验证会话被创建
        assert len(agent.user_sessions) > 0
        
        # 验证会话包含块数据
        for session in agent.user_sessions.values():
            assert 'chunks' in session
            assert 'key_concepts' in session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
