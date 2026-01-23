import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm_client import LLMClient

@pytest.fixture
def llm_client():
    return LLMClient()

@pytest.mark.asyncio
async def test_llm_client_initialization():
    """测试LLM客户端初始化"""
    client = LLMClient()
    assert client.model == "gpt-4-turbo-preview"
    assert client.api_key is not None or client.api_key == ""
    assert hasattr(client, 'client')
    assert len(client.extension_templates) == 3  # default, technical, simple

@pytest.mark.asyncio
async def test_extend_knowledge_with_mock():
    """测试知识扩展（使用mock）"""
    with patch('app.llm_client.AsyncOpenAI') as mock_openai:
        # 配置mock
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{"extended_content": "Test content", "sections": ["Test"]}'
        
        mock_completion = AsyncMock(return_value=mock_response)
        mock_openai.return_value.chat.completions.create = mock_completion
        
        client = LLMClient()
        result = await client.extend_knowledge("Test content")
        
        assert result is not None
        assert "extended_content" in result
        assert "sections" in result

@pytest.mark.asyncio
async def test_extend_knowledge_error_handling():
    """测试知识扩展的错误处理"""
    with patch('app.llm_client.AsyncOpenAI') as mock_openai:
        # 模拟异常
        mock_openai.return_value.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        
        client = LLMClient()
        result = await client.extend_knowledge("Test content")
        
        # 应该返回降级结果
        assert "error" in result
        assert "fallback" in result
        assert result["fallback"] == True

def test_prompt_templates():
    """测试Prompt模板"""
    client = LLMClient()
    
    assert "default" in client.extension_templates
    assert "technical" in client.extension_templates
    assert "simple" in client.extension_templates
    
    # 测试模板格式化
    template = client.extension_templates["default"]
    formatted = template.format(title="Test", content="Content")
    assert "Test" in formatted
    assert "Content" in formatted