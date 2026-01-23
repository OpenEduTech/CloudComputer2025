import pytest
from unittest.mock import Mock, patch, MagicMock
from models.question_generator import QuestionGenerator
from models import Chunk, Question
from models.config import Config


class TestQuestionGenerator:
    """QuestionGenerator 单元测试"""
    
    @pytest.fixture
    def config(self):
        """创建配置"""
        config = Mock(spec=Config)
        config.OPENAI_API_KEY = "test-key"
        config.OPENAI_BASE_URL = "https://api.openai.com/v1"
        config.OPENAI_MODEL = "gpt-3.5-turbo"
        config.QUESTION_TYPES = ["multiple_choice", "short_answer", "true_false"]
        return config
    
    @pytest.fixture
    def sample_chunks(self):
        """创建示例学习资料分块"""
        return [
            Chunk(
                text="机器学习是人工智能的重要分支，通过数据驱动的方式自动学习模型。",
                metadata={"source": "intro", "page": 1}
            ),
            Chunk(
                text="过拟合发生在模型过于复杂时，训练数据拟合很好，但新数据表现差。",
                metadata={"source": "concepts", "page": 2}
            ),
            Chunk(
                text="交叉验证是一种评估模型泛化能力的技术，通过多轮训练评估来提高评估的可靠性。",
                metadata={"source": "techniques", "page": 3}
            )
        ]
    
    @pytest.fixture
    def generator(self, config):
        """创建题目生成器"""
        with patch('models.question_generator.OpenAI'):
            return QuestionGenerator(config)
    
    def test_generator_initialization(self, generator, config):
        """测试：生成器正确初始化"""
        assert generator is not None
        assert generator.config == config
    
    def test_select_difficulty_distribution(self, generator):
        """测试：难度分布正确"""
        num_questions = 10
        difficulties = []
        
        for i in range(num_questions):
            diff = generator._select_difficulty(i, num_questions)
            difficulties.append(diff)
        
        # 验证难度分布合理
        assert "easy" in difficulties
        assert "medium" in difficulties or "hard" in difficulties
        assert all(d in ["easy", "medium", "hard"] for d in difficulties)
    
    def test_extract_key_concepts(self, generator, sample_chunks):
        """测试：关键概念提取"""
        with patch.object(generator.client.chat.completions, 'create') as mock_create:
            # 模拟 API 响应
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="机器学习\n过拟合\n交叉验证"))]
            mock_create.return_value = mock_response
            
            concepts = generator._extract_key_concepts_for_questions(sample_chunks)
            
            assert concepts is not None
            assert "concepts" in concepts
            assert len(concepts["concepts"]) > 0


class TestQuestionGeneratorStream:
    """流式生成题目测试"""
    
    @pytest.fixture
    def config(self):
        """创建配置"""
        config = Mock(spec=Config)
        config.OPENAI_API_KEY = "test-key"
        config.OPENAI_BASE_URL = "https://api.openai.com/v1"
        config.OPENAI_MODEL = "gpt-3.5-turbo"
        config.QUESTION_TYPES = ["multiple_choice"]
        return config
    
    @pytest.fixture
    def sample_chunks(self):
        """创建示例分块"""
        return [
            Chunk(
                text="机器学习基础：定义、历史和应用。",
                metadata={"source": "intro"}
            )
        ]
    
    @pytest.fixture
    def generator(self, config):
        """创建生成器"""
        with patch('models.question_generator.OpenAI'):
            return QuestionGenerator(config)
    
    def test_stream_callbacks_are_called(self, generator, sample_chunks):
        """测试：流式回调被正确调用"""
        callback_calls = {
            'start': [],
            'chunk': [],
            'complete': []
        }
        
        def on_start(curr, total):
            callback_calls['start'].append((curr, total))
        
        def on_chunk(text):
            callback_calls['chunk'].append(text)
        
        def on_complete(question):
            callback_calls['complete'].append(question)
        
        # 模拟 API 流式响应
        with patch.object(generator.client.chat.completions, 'create') as mock_create:
            # 创建模拟流响应
            mock_stream = [
                Mock(choices=[Mock(delta=Mock(content='{"question"'))]),
                Mock(choices=[Mock(delta=Mock(content=': "test"'))]),
                Mock(choices=[Mock(delta=Mock(content='}'))]),
            ]
            
            mock_cm = MagicMock()
            mock_cm.__enter__.return_value = mock_stream
            mock_cm.__exit__.return_value = False
            mock_create.return_value = mock_cm
            
            # 这里会因为 JSON 不完整而失败，但可以验证回调机制
            try:
                generator.generate_questions_stream(
                    sample_chunks,
                    num_questions=1,
                    on_question_start=on_start,
                    on_question_chunk=on_chunk,
                    on_question_complete=on_complete
                )
            except:
                pass
            
            # 验证回调被调用
            assert len(callback_calls['start']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
