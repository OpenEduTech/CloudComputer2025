"""Mock数据 - 用于测试和演示"""

# Mock概念挖掘响应
MOCK_DISCOVER_RESPONSE = {
    "status": "success",
    "request_id": "req_123456",
    "data": {
        "nodes": [
            {
                "id": "entropy_xinxilun",
                "label": "熵",
                "discipline": "信息论",
                "definition": "信息的不确定性度量",
                "credibility": 0.95
            },
            {
                "id": "shannon_entropy_xinxilun",
                "label": "香农熵",
                "discipline": "信息论",
                "definition": "信息论中熵的具体数学定义，H(X) = -Σ p(x)log p(x)",
                "credibility": 0.92
            },
            {
                "id": "thermodynamic_entropy_wuli",
                "label": "热力学熵",
                "discipline": "物理",
                "definition": "热力学中描述系统无序程度的状态函数",
                "credibility": 0.90
            },
            {
                "id": "cross_entropy_jisuanji",
                "label": "交叉熵",
                "discipline": "计算机",
                "definition": "机器学习中用于度量两个概率分布差异的损失函数",
                "credibility": 0.88
            }
        ],
        "edges": [
            {
                "source": "entropy_xinxilun",
                "target": "shannon_entropy_xinxilun",
                "relation": "is_foundation_of",
                "weight": 0.92,
                "reasoning": "香农熵是信息论中熵的具体定义，使用概率分布的对数期望来量化信息量"
            },
            {
                "source": "entropy_xinxilun",
                "target": "thermodynamic_entropy_wuli",
                "relation": "similar_to",
                "weight": 0.88,
                "reasoning": "信息熵与热力学熵在数学形式上完全一致，都用于度量系统的不确定性或无序程度"
            },
            {
                "source": "shannon_entropy_xinxilun",
                "target": "cross_entropy_jisuanji",
                "relation": "applied_in",
                "weight": 0.85,
                "reasoning": "交叉熵在机器学习中直接应用香农熵的概念，用于衡量预测分布与真实分布的差异"
            }
        ],
        "metadata": {
            "total_nodes": 4,
            "total_edges": 3,
            "verified_nodes": 4,
            "avg_credibility": 0.91,
            "processing_time": 12.5
        }
    }
}

# Mock概念验证响应
MOCK_VERIFY_RESPONSE = {
    "status": "success",
    "request_id": "req_789012",
    "data": {
        "credibility_score": 0.92,
        "is_valid": True,
        "evidence": [
            {
                "source": "Wikipedia",
                "url": "https://zh.wikipedia.org/wiki/香农熵",
                "snippet": "香农熵是信息论的基本概念，由克劳德·香农在1948年提出，用于量化信息的不确定性..."
            },
            {
                "source": "学术论文",
                "url": "https://doi.org/10.1002/j.1538-7305.1948.tb01338.x",
                "snippet": "Shannon, C. E. (1948). A Mathematical Theory of Communication. Bell System Technical Journal."
            }
        ],
        "warnings": []
    }
}

# Mock节点扩展响应
MOCK_EXPAND_RESPONSE = {
    "status": "success",
    "request_id": "req_345678",
    "data": {
        "new_nodes": [
            {
                "id": "kl_divergence_jisuanji",
                "label": "KL散度",
                "discipline": "计算机",
                "definition": "衡量两个概率分布之间差异的非对称度量",
                "credibility": 0.87
            },
            {
                "id": "mutual_information_xinxilun",
                "label": "互信息",
                "discipline": "信息论",
                "definition": "两个随机变量之间相互依赖程度的度量",
                "credibility": 0.86
            }
        ],
        "new_edges": [
            {
                "source": "shannon_entropy_xinxilun",
                "target": "kl_divergence_jisuanji",
                "relation": "is_foundation_of",
                "weight": 0.83,
                "reasoning": "KL散度基于香农熵定义，用于比较两个概率分布"
            },
            {
                "source": "shannon_entropy_xinxilun",
                "target": "mutual_information_xinxilun",
                "relation": "is_foundation_of",
                "weight": 0.81,
                "reasoning": "互信息通过香农熵来定义，I(X;Y) = H(X) + H(Y) - H(X,Y)"
            }
        ],
        "metadata": {
            "parent_node_id": "shannon_entropy_xinxilun",
            "expansion_depth": 1
        }
    }
}

# Mock概念列表（用于测试）
MOCK_CONCEPTS = [
    {
        "concept_name": "神经网络",
        "discipline": "计算机",
        "definition": "模仿生物神经系统的计算模型",
        "credibility": 0.95,
        "strength": 0.92,
        "relation_type": "applied_in",
        "reasoning": "机器学习中广泛使用神经网络进行模式识别"
    },
    {
        "concept_name": "反向传播",
        "discipline": "数学",
        "definition": "训练神经网络的核心算法",
        "credibility": 0.93,
        "strength": 0.90,
        "relation_type": "is_foundation_of",
        "reasoning": "反向传播基于链式法则计算梯度"
    },
    {
        "concept_name": "激活函数",
        "discipline": "数学",
        "definition": "神经网络中引入非线性的函数",
        "credibility": 0.91,
        "strength": 0.88,
        "relation_type": "similar_to",
        "reasoning": "激活函数类似于生物神经元的激活机制"
    }
]
