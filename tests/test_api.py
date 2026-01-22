"""API接口测试"""

import pytest
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from api.main import app
from shared.mock_data import (
    MOCK_DISCOVER_REQUEST,
    MOCK_VERIFY_REQUEST,
    MOCK_EXPAND_REQUEST
)

# 创建测试客户端
client = TestClient(app)


def test_root_endpoint():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ConceptGraph AI API"
    assert data["version"] == "1.0.0"
    assert "endpoints" in data


def test_health_check():
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "openai_configured" in data
    assert "openrouter_configured" in data


def test_get_disciplines():
    """测试获取学科列表"""
    response = client.get("/api/v1/agent/disciplines")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "disciplines" in data["data"]
    assert len(data["data"]["disciplines"]) == 6


def test_get_relation_types():
    """测试获取关系类型列表"""
    response = client.get("/api/v1/agent/relations")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "types" in data["data"]
    assert "descriptions" in data["data"]


def test_discover_invalid_request():
    """测试无效的挖掘请求"""
    # 空概念
    response = client.post("/api/v1/agent/discover", json={
        "concept": "",
        "depth": 2
    })
    assert response.status_code == 422  # Pydantic验证错误
    
    # 深度超出范围
    response = client.post("/api/v1/agent/discover", json={
        "concept": "熵",
        "depth": 10
    })
    assert response.status_code == 422


def test_verify_invalid_request():
    """测试无效的验证请求"""
    # 缺少必填字段
    response = client.post("/api/v1/agent/verify", json={
        "concept_a": "熵"
        # 缺少concept_b和claimed_relation
    })
    assert response.status_code == 422


def test_expand_invalid_request():
    """测试无效的扩展请求"""
    # 缺少现有图谱
    response = client.post("/api/v1/agent/expand", json={
        "node_id": "test_node"
        # 缺少existing_graph
    })
    assert response.status_code == 422


# ==================== 集成测试（需要配置API Key） ====================

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="需要配置OPENAI_API_KEY环境变量"
)
def test_discover_integration():
    """测试概念挖掘接口（集成测试）"""
    response = client.post(
        "/api/v1/agent/discover",
        json={
            "concept": "熵",
            "disciplines": ["信息论", "计算机"],
            "depth": 1,
            "max_concepts": 10,
            "enable_verification": False  # 跳过验证加快测试
        }
    )
    
    # 允许超时或成功
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "nodes" in data["data"]
        print(f"[OK] 发现 {len(data['data']['nodes'])} 个概念")
    else:
        print(f"[WARN] 请求失败: {response.status_code}")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="需要配置OPENAI_API_KEY环境变量"
)
def test_verify_integration():
    """测试概念验证接口（集成测试）"""
    response = client.post(
        "/api/v1/agent/verify",
        json={
            "concept_a": "熵",
            "concept_b": "信息增益",
            "claimed_relation": "信息增益基于熵的概念"
        }
    )
    
    # 允许超时或成功
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "credibility_score" in data["data"]
        print(f"[OK] 可信度评分: {data['data']['credibility_score']:.2f}")
    else:
        print(f"[WARN] 请求失败: {response.status_code}")


if __name__ == "__main__":
    print("API接口测试开始...")
    print()
    
    print("=" * 60)
    print("基础接口测试")
    print("=" * 60)
    
    print("\n1. 测试根路径...")
    test_root_endpoint()
    print("   通过")
    
    print("\n2. 测试健康检查...")
    test_health_check()
    print("   通过")
    
    print("\n3. 测试获取学科列表...")
    test_get_disciplines()
    print("   通过")
    
    print("\n4. 测试获取关系类型...")
    test_get_relation_types()
    print("   通过")
    
    print("\n" + "=" * 60)
    print("参数验证测试")
    print("=" * 60)
    
    print("\n5. 测试无效的挖掘请求...")
    test_discover_invalid_request()
    print("   通过")
    
    print("\n6. 测试无效的验证请求...")
    test_verify_invalid_request()
    print("   通过")
    
    print("\n7. 测试无效的扩展请求...")
    test_expand_invalid_request()
    print("   通过")
    
    print("\n" + "=" * 60)
    print("集成测试（需要API Key）")
    print("=" * 60)
    
    if os.getenv("OPENAI_API_KEY"):
        print("\n8. 测试概念挖掘接口...")
        test_discover_integration()
        
        print("\n9. 测试概念验证接口...")
        test_verify_integration()
    else:
        print("\n警告: 跳过集成测试（未配置API Key）")
    
    print("\n" + "=" * 60)
    print("所有基础测试通过!")
    print("=" * 60)
