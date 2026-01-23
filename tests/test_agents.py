"""Agent单元测试"""

import pytest
import asyncio
from agents.orchestrator import AgentOrchestrator
from agents.concept_discovery_agent import ConceptDiscoveryAgent
from agents.verification_agent import VerificationAgent
from agents.graph_builder_agent import GraphBuilderAgent
from shared.constants import Discipline


@pytest.fixture
def orchestrator():
    """创建编排器实例"""
    return AgentOrchestrator()


@pytest.fixture
def discovery_agent():
    """创建发现Agent实例"""
    return ConceptDiscoveryAgent()


@pytest.fixture
def verification_agent():
    """创建验证Agent实例"""
    return VerificationAgent()


@pytest.fixture
def graph_builder_agent():
    """创建图谱构建Agent实例"""
    return GraphBuilderAgent()


# ==================== ConceptDiscoveryAgent测试 ====================

@pytest.mark.asyncio
async def test_discover_concepts_basic(discovery_agent):
    """测试基础概念发现"""
    result = await discovery_agent.discover_concepts(
        concept="熵",
        disciplines=[Discipline.MATH, Discipline.PHYSICS],
        depth=1,
        max_concepts=5
    )
    
    assert result is not None
    assert 'source_concept' in result
    assert result['source_concept'] == "熵"
    assert 'related_concepts' in result
    assert isinstance(result['related_concepts'], list)


@pytest.mark.asyncio
async def test_discover_concepts_all_disciplines(discovery_agent):
    """测试全学科概念发现"""
    result = await discovery_agent.discover_concepts(
        concept="神经网络",
        disciplines=Discipline.ALL,
        depth=2,
        max_concepts=20
    )
    
    assert result is not None
    assert len(result['related_concepts']) > 0
    
    # 检查是否覆盖多个学科
    disciplines_found = set(
        c.get('discipline') for c in result['related_concepts']
    )
    assert len(disciplines_found) >= 2


# ==================== VerificationAgent测试 ====================

@pytest.mark.asyncio
async def test_verify_relation(verification_agent):
    """测试关联验证"""
    result = await verification_agent.verify_relation(
        concept_a="熵",
        concept_b="香农熵",
        claimed_relation="香农熵是信息论中熵的具体定义",
        strength=0.95
    )
    
    assert result is not None
    assert 'credibility_score' in result
    assert 'is_valid' in result
    assert isinstance(result['credibility_score'], float)
    assert 0.0 <= result['credibility_score'] <= 1.0


# ==================== GraphBuilderAgent测试 ====================

@pytest.mark.asyncio
async def test_build_graph(graph_builder_agent):
    """测试图谱构建"""
    # Mock数据
    mock_concepts = [
        {
            "concept_name": "香农熵",
            "discipline": "信息论",
            "definition": "信息的不确定性度量",
            "credibility": 0.95,
            "strength": 0.92,
            "relation_type": "is_foundation_of",
            "reasoning": "香农熵是信息论中熵的具体定义"
        },
        {
            "concept_name": "热力学熵",
            "discipline": "物理",
            "definition": "系统无序程度的度量",
            "credibility": 0.90,
            "strength": 0.88,
            "relation_type": "similar_to",
            "reasoning": "都用于度量系统的不确定性"
        }
    ]
    
    result = await graph_builder_agent.build_graph(
        source_concept="熵",
        verified_concepts=mock_concepts
    )
    
    assert result is not None
    assert 'nodes' in result
    assert 'edges' in result
    assert 'metadata' in result
    assert len(result['nodes']) >= 2
    assert len(result['edges']) >= 1


@pytest.mark.asyncio
async def test_merge_graphs(graph_builder_agent):
    """测试图谱合并"""
    graph1 = {
        "nodes": [
            {"id": "node1", "label": "概念1", "discipline": "数学", "definition": "定义1", "credibility": 0.9}
        ],
        "edges": []
    }
    
    graph2 = {
        "nodes": [
            {"id": "node2", "label": "概念2", "discipline": "物理", "definition": "定义2", "credibility": 0.85}
        ],
        "edges": []
    }
    
    result = await graph_builder_agent.merge_graphs(graph1, graph2)
    
    assert result is not None
    assert len(result['nodes']) == 2
    assert 'merged_from' in result['metadata']


# ==================== AgentOrchestrator测试 ====================

@pytest.mark.asyncio
async def test_orchestrator_discover(orchestrator):
    """测试编排器完整流程"""
    response = await orchestrator.discover(
        concept="测试概念",
        disciplines=[Discipline.COMPUTER],
        depth=1,
        max_concepts=3,
        enable_verification=False  # 跳过验证以加快测试
    )
    
    assert response is not None
    assert response.status in ["success", "error"]
    assert response.request_id is not None
    
    if response.status == "success" and response.data:
        assert hasattr(response.data, 'nodes')
        assert hasattr(response.data, 'edges')
        assert hasattr(response.data, 'metadata')


# ==================== 工具函数测试 ====================

def test_generate_node_id():
    """测试节点ID生成"""
    from shared.utils import generate_node_id
    
    node_id = generate_node_id("熵", "信息论")
    assert node_id is not None
    assert isinstance(node_id, str)
    assert "_" in node_id


def test_calculate_avg_credibility():
    """测试平均可信度计算"""
    from shared.utils import calculate_avg_credibility
    
    class MockNode:
        def __init__(self, credibility):
            self.credibility = credibility
    
    nodes = [MockNode(0.9), MockNode(0.8), MockNode(0.7)]
    avg = calculate_avg_credibility(nodes)
    
    assert avg == pytest.approx(0.8, 0.01)


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
