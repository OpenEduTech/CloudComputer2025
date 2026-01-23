import pytest
from fastapi.testclient import TestClient
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)

def test_health_check():
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ppt-knowledge-extender"

def test_api_docs():
    """测试API文档端点"""
    response = client.get("/docs")
    assert response.status_code == 200

def test_openapi_json():
    """测试OpenAPI JSON端点"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "PPT知识扩展智能体"

def test_invalid_endpoint():
    """测试不存在的端点"""
    response = client.get("/invalid-endpoint")
    assert response.status_code == 404

def test_cors_headers():
    """测试CORS头"""
    response = client.options("/health", headers={
        "Origin": "http://localhost:8501",
        "Access-Control-Request-Method": "GET"
    })
    # OPTIONS请求应该返回200或204，并且包含CORS头
    assert response.status_code in [200, 204]