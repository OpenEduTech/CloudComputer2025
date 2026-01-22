"""Mock测试数据 - 用于API接口测试"""

from shared.schemas import ConceptNode, ConceptEdge


# ==================== Mock概念节点 ====================

MOCK_NODES = [
    ConceptNode(
        id="entropy_xinxilun",
        label="熵",
        discipline="信息论",
        definition="信息的不确定性度量",
        credibility=0.95,
        metadata={"source": "Wikipedia", "verified": True}
    ),
    ConceptNode(
        id="shannon_entropy_xinxilun",
        label="香农熵",
        discipline="信息论",
        definition="离散随机变量的平均信息量",
        credibility=0.92,
        metadata={"source": "Wikipedia", "verified": True}
    ),
    ConceptNode(
        id="information_gain_jisuanji",
        label="信息增益",
        discipline="计算机",
        definition="决策树学习中用于特征选择的度量",
        credibility=0.88,
        metadata={"source": "Arxiv", "verified": True}
    ),
    ConceptNode(
        id="cross_entropy_jisuanji",
        label="交叉熵",
        discipline="计算机",
        definition="衡量两个概率分布的差异",
        credibility=0.90,
        metadata={"source": "Wikipedia", "verified": True}
    ),
    ConceptNode(
        id="thermodynamic_entropy_wuli",
        label="热力学熵",
        discipline="物理",
        definition="系统混乱程度的度量",
        credibility=0.94,
        metadata={"source": "Wikipedia", "verified": True}
    ),
    ConceptNode(
        id="boltzmann_entropy_wuli",
        label="玻尔兹曼熵",
        discipline="物理",
        definition="统计物理中描述系统微观状态数",
        credibility=0.93,
        metadata={"source": "Wikipedia", "verified": True}
    ),
    ConceptNode(
        id="information_theory_shuxue",
        label="信息论",
        discipline="数学",
        definition="研究信息的量化、存储和通信的数学理论",
        credibility=0.96,
        metadata={"source": "Wikipedia", "verified": True}
    ),
    ConceptNode(
        id="probability_distribution_shuxue",
        label="概率分布",
        discipline="数学",
        definition="描述随机变量取值的概率规律",
        credibility=0.95,
        metadata={"source": "Wikipedia", "verified": True}
    ),
]


# ==================== Mock关系边 ====================

MOCK_EDGES = [
    ConceptEdge(
        source="entropy_xinxilun",
        target="shannon_entropy_xinxilun",
        relation="is_foundation_of",
        weight=0.92,
        reasoning="香农熵是信息论中熵的具体定义，用于度量信息的不确定性"
    ),
    ConceptEdge(
        source="shannon_entropy_xinxilun",
        target="information_gain_jisuanji",
        relation="is_foundation_of",
        weight=0.85,
        reasoning="信息增益基于香农熵计算，用于评估特征的重要性"
    ),
    ConceptEdge(
        source="shannon_entropy_xinxilun",
        target="cross_entropy_jisuanji",
        relation="derived_from",
        weight=0.88,
        reasoning="交叉熵是香农熵的扩展，用于比较两个概率分布"
    ),
    ConceptEdge(
        source="entropy_xinxilun",
        target="thermodynamic_entropy_wuli",
        relation="similar_to",
        weight=0.75,
        reasoning="信息熵和热力学熵都描述系统的不确定性或混乱程度"
    ),
    ConceptEdge(
        source="thermodynamic_entropy_wuli",
        target="boltzmann_entropy_wuli",
        relation="generalizes",
        weight=0.90,
        reasoning="玻尔兹曼熵是热力学熵的微观统计解释"
    ),
    ConceptEdge(
        source="information_theory_shuxue",
        target="entropy_xinxilun",
        relation="is_foundation_of",
        weight=0.95,
        reasoning="信息论是研究熵及信息量化的数学基础"
    ),
    ConceptEdge(
        source="probability_distribution_shuxue",
        target="shannon_entropy_xinxilun",
        relation="is_foundation_of",
        weight=0.90,
        reasoning="香农熵基于概率分布计算，描述随机变量的不确定性"
    ),
]


# ==================== Mock图谱数据 ====================

MOCK_GRAPH = {
    "nodes": [node.model_dump() for node in MOCK_NODES],
    "edges": [edge.model_dump() for edge in MOCK_EDGES],
    "metadata": {
        "total_nodes": len(MOCK_NODES),
        "total_edges": len(MOCK_EDGES),
        "verified_nodes": len([n for n in MOCK_NODES if n.credibility >= 0.5]),
        "avg_credibility": sum(n.credibility for n in MOCK_NODES) / len(MOCK_NODES),
        "processing_time": 10.5
    }
}


# ==================== Mock请求示例 ====================

MOCK_DISCOVER_REQUEST = {
    "concept": "熵",
    "disciplines": ["数学", "物理", "信息论", "计算机"],
    "depth": 2,
    "max_concepts": 30,
    "enable_verification": True
}

MOCK_VERIFY_REQUEST = {
    "concept_a": "熵",
    "concept_b": "信息增益",
    "claimed_relation": "信息增益基于熵的概念，用于度量信息的期望减少量",
    "strength": 0.8
}

MOCK_EXPAND_REQUEST = {
    "node_id": "entropy_xinxilun",
    "existing_graph": {
        "nodes": [MOCK_NODES[0].model_dump()],
        "edges": []
    },
    "disciplines": ["计算机", "数学"],
    "max_new_nodes": 10
}


# ==================== Mock响应示例 ====================

MOCK_DISCOVER_RESPONSE = {
    "status": "success",
    "request_id": "req_20260117_123456",
    "data": MOCK_GRAPH
}

MOCK_VERIFY_RESPONSE = {
    "status": "success",
    "request_id": "req_20260117_123457",
    "data": {
        "credibility_score": 0.87,
        "is_valid": True,
        "evidence": [
            {
                "source": "Wikipedia",
                "url": "https://zh.wikipedia.org/wiki/信息增益",
                "snippet": "信息增益是决策树学习中的一个重要概念，基于熵来度量特征对分类的贡献..."
            },
            {
                "source": "Arxiv",
                "url": "https://arxiv.org/abs/1234.5678",
                "snippet": "Information gain is calculated using entropy to evaluate feature importance..."
            }
        ],
        "warnings": []
    }
}

MOCK_EXPAND_RESPONSE = {
    "status": "success",
    "data": {
        "nodes": [
            MOCK_NODES[0].model_dump(),
            MOCK_NODES[2].model_dump(),
            MOCK_NODES[3].model_dump()
        ],
        "edges": [
            MOCK_EDGES[1].model_dump(),
            MOCK_EDGES[2].model_dump()
        ],
        "metadata": {
            "parent_node_id": "entropy_xinxilun",
            "new_nodes_count": 2,
            "expansion_depth": 1
        }
    }
}


# ==================== Mock错误响应 ====================

MOCK_ERROR_RESPONSES = {
    "invalid_request": {
        "status": "error",
        "error_code": "ERR_1001",
        "message": "请求参数无效"
    },
    "no_concepts_found": {
        "status": "error",
        "error_code": "ERR_2005",
        "message": "未找到相关概念，请尝试其他关键词"
    },
    "llm_api_error": {
        "status": "error",
        "error_code": "ERR_2001",
        "message": "大模型调用失败，请稍后重试",
        "details": "Connection timeout"
    },
    "verification_failed": {
        "status": "error",
        "error_code": "ERR_2004",
        "message": "概念验证失败"
    },
    "concept_not_found": {
        "status": "error",
        "error_code": "ERR_4001",
        "message": "概念不存在"
    }
}


# ==================== 辅助函数 ====================

def get_mock_node_by_id(node_id: str) -> ConceptNode:
    """根据ID获取Mock节点"""
    for node in MOCK_NODES:
        if node.id == node_id:
            return node
    raise ValueError(f"Node not found: {node_id}")


def get_mock_edges_by_source(source_id: str) -> list[ConceptEdge]:
    """获取指定源节点的所有边"""
    return [edge for edge in MOCK_EDGES if edge.source == source_id]


def get_mock_graph_subset(node_ids: list[str]) -> dict:
    """获取图谱子集"""
    nodes = [n for n in MOCK_NODES if n.id in node_ids]
    edges = [
        e for e in MOCK_EDGES
        if e.source in node_ids and e.target in node_ids
    ]
    
    return {
        "nodes": [node.model_dump() for node in nodes],
        "edges": [edge.model_dump() for edge in edges],
        "metadata": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "verified_nodes": len([n for n in nodes if n.credibility >= 0.5]),
            "avg_credibility": sum(n.credibility for n in nodes) / len(nodes) if nodes else 0.0,
            "processing_time": 5.0
        }
    }
