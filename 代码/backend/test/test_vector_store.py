import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.vector_store import VectorStore

@pytest.fixture
def mock_milvus():
    """模拟Milvus连接"""
    with patch('app.vector_store.connections') as mock_connections:
        with patch('app.vector_store.Collection') as mock_collection:
            with patch('app.vector_store.SentenceTransformer') as mock_embedding:
                # 配置mock
                mock_connections.has_collection.return_value = True
                mock_embedding.return_value.encode.return_value = [0.1] * 384
                
                mock_col_instance = MagicMock()
                mock_insert_result = MagicMock()
                mock_insert_result.primary_keys = [1]
                mock_col_instance.insert.return_value = mock_insert_result
                mock_col_instance.flush.return_value = None
                
                mock_collection.return_value = mock_col_instance
                
                yield mock_col_instance

def test_vector_store_initialization(mock_milvus):
    """测试向量存储初始化"""
    with patch('app.vector_store.connections') as mock_connections:
        mock_connections.connect.return_value = None
        mock_connections.has_collection.return_value = True
        
        store = VectorStore()
        assert store.host == "localhost"
        assert store.port == "19530"
        assert store.collection_name == "ppt_slides"
        assert store.collection is not None

def test_add_document(mock_milvus):
    """测试添加文档"""
    with patch('app.vector_store.connections') as mock_connections:
        mock_connections.has_collection.return_value = True
        
        store = VectorStore()
        doc_id = store.add_document(
            text="Test document content",
            metadata={"ppt_id": "test-123", "page_num": 1, "title": "Test"}
        )
        
        assert doc_id == 1
        mock_milvus.insert.assert_called_once()
        mock_milvus.flush.assert_called_once()

def test_search_similar(mock_milvus):
    """测试搜索相似内容"""
    with patch('app.vector_store.connections') as mock_connections:
        mock_connections.has_collection.return_value = True
        
        # 模拟搜索结果
        mock_hit = MagicMock()
        mock_hit.id = 1
        mock_hit.score = 0.95
        mock_hit.entity.get.side_effect = lambda x: {
            "content": "Test content",
            "title": "Test title",
            "page_num": 1,
            "metadata": '{"ppt_id": "test-123"}'
        }.get(x)
        
        mock_search_result = MagicMock()
        mock_search_result.__iter__.return_value = iter([[mock_hit]])
        
        mock_milvus.search.return_value = mock_search_result
        
        store = VectorStore()
        results = store.search_similar("test query", top_k=5)
        
        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["score"] == 0.95
        assert results[0]["content"] == "Test content"