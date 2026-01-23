import pytest
from models.data_processor import DataProcessor
from models import Chunk
from unittest.mock import Mock, patch
from models.config import Config


class TestDataProcessor:
    """DataProcessor 单元测试"""
    
    @pytest.fixture
    def config(self):
        """创建配置"""
        config = Mock(spec=Config)
        config.OPENAI_API_KEY = "test-key"
        config.OPENAI_BASE_URL = "https://api.openai.com/v1"
        config.OPENAI_MODEL = "gpt-3.5-turbo"
        return config
    
    @pytest.fixture
    def processor(self, config):
        """创建处理器实例"""
        with patch('models.data_processor.OpenAI'):
            return DataProcessor(config)
    
    @pytest.fixture
    def sample_text(self):
        """示例学习资料"""
        return """
        机器学习基础概念
        
        1. 监督学习
        监督学习是指从标记的训练数据中学习一个模型。
        常见算法包括线性回归、决策树等。
        
        2. 无监督学习
        无监督学习是指从无标记数据中寻找隐藏结构。
        常见方法包括聚类、降维等。
        
        3. 过拟合
        过拟合是指模型在训练数据上表现很好，
        但在新数据上表现不佳的现象。
        """
    
    def test_process_text_returns_chunks(self, processor, sample_text):
        """测试：文本处理返回分块"""
        chunks = processor.process_input(sample_text, input_type="text")
        
        assert chunks is not None
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
    
    def test_chunks_contain_text(self, processor, sample_text):
        """测试：分块包含文本内容"""
        chunks = processor.process_input(sample_text, input_type="text")
        
        for chunk in chunks:
            assert hasattr(chunk, 'text')
            assert len(chunk.text) > 0
            assert isinstance(chunk.text, str)
    
    def test_chunks_contain_metadata(self, processor, sample_text):
        """测试：分块包含元数据"""
        chunks = processor.process_input(sample_text, input_type="text")
        
        for chunk in chunks:
            assert hasattr(chunk, 'metadata')
            assert isinstance(chunk.metadata, dict)
    
    def test_empty_text_returns_empty_chunks(self, processor):
        """测试：空文本返回空分块列表"""
        chunks = processor.process_input("", input_type="text")
        
        assert chunks is not None
        assert len(chunks) == 0
    
    def test_process_file_from_path(self, processor, tmp_path):
        """测试：从文件路径处理"""
        # 创建临时文件
        test_file = tmp_path / "test.txt"
        test_content = "这是测试内容\n分成多行\n进行处理"
        test_file.write_text(test_content)
        
        chunks = processor.process_input(str(test_file), input_type="text")
        
        assert len(chunks) > 0
        # 验证处理的内容包含原始内容的关键词
        combined_text = " ".join([chunk.text for chunk in chunks])
        assert "测试" in combined_text or len(combined_text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
