# Agent API接口文档

## 一、概述

本文档定义了成员A（智能体组）提供给成员B（架构组）的API接口规范。

**基础URL**: `/api/v1/agent`

**请求格式**: JSON

**响应格式**: JSON

**超时时间**: 60秒

## 二、接口列表

### 2.1 概念挖掘接口

**接口名称**: `discover_concepts`

**URL**: `POST /api/v1/agent/discover`

**描述**: 发现跨学科相关概念，构建知识图谱

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| concept | string | 是 | 核心概念词，1-50字符 |
| disciplines | string[] | 否 | 目标学科列表，默认全部学科 |
| depth | int | 否 | 挖掘深度，默认2，范围[1-3] |
| max_concepts | int | 否 | 最大概念数，默认30，范围[10-100] |

**请求示例**:

```json
{
  "concept": "熵",
  "disciplines": ["数学", "物理", "信息论", "计算机"],
  "depth": 2,
  "max_concepts": 30
}
```

**成功响应** (200):

```json
{
  "status": "success",
  "request_id": "req_abc123def456",
  "data": {
    "nodes": [
      {
        "id": "entropy_xinxilun",
        "label": "熵",
        "discipline": "信息论",
        "definition": "信息的不确定性度量",
        "credibility": 0.95
      }
    ],
    "edges": [
      {
        "source": "entropy_xinxilun",
        "target": "shannon_entropy_xinxilun",
        "relation": "is_foundation_of",
        "weight": 0.92,
        "reasoning": "香农熵是信息论中熵的具体定义"
      }
    ],
    "metadata": {
      "total_nodes": 18,
      "total_edges": 24,
      "verified_nodes": 16,
      "avg_credibility": 0.87,
      "processing_time": 12.5
    }
  }
}
```

**错误响应** (4xx/5xx):

```json
{
  "status": "error",
  "request_id": "req_abc123def456",
  "error_code": "ERR_2005",
  "message": "未找到相关概念，请尝试其他关键词",
  "details": {
    "concept": "测试概念",
    "reason": "LLM未返回有效结果"
  }
}
```

---

### 2.2 概念验证接口

**接口名称**: `verify_concept_relation`

**URL**: `POST /api/v1/agent/verify`

**描述**: 验证两个概念之间的关联是否准确

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| concept_a | string | 是 | 概念A |
| concept_b | string | 是 | 概念B |
| claimed_relation | string | 是 | 声称的关联描述 |
| strength | float | 否 | 声称的关联强度，默认0.5 |

**请求示例**:

```json
{
  "concept_a": "熵",
  "concept_b": "信息增益",
  "claimed_relation": "信息增益基于熵的概念",
  "strength": 0.85
}
```

**成功响应** (200):

```json
{
  "status": "success",
  "request_id": "req_xyz789abc012",
  "data": {
    "credibility_score": 0.92,
    "is_valid": true,
    "evidence": [
      {
        "source": "Wikipedia",
        "url": "https://zh.wikipedia.org/wiki/信息增益",
        "snippet": "信息增益是决策树算法中的核心概念，基于香农熵来衡量特征的重要性..."
      },
      {
        "source": "学术论文",
        "url": "https://doi.org/10.1023/A:1007456727198",
        "snippet": "Information Gain is defined using Shannon entropy..."
      }
    ],
    "warnings": []
  }
}
```

**错误响应**:

```json
{
  "status": "error",
  "request_id": "req_xyz789abc012",
  "error_code": "ERR_2004",
  "message": "概念验证失败",
  "details": {
    "reason": "LLM API超时"
  }
}
```

---

### 2.3 图谱增量扩展接口

**接口名称**: `expand_concept`

**URL**: `POST /api/v1/agent/expand`

**描述**: 扩展已存在的节点，发现子概念或相关应用

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| node_id | string | 是 | 要扩展的节点ID |
| disciplines | string[] | 否 | 限定扩展的学科 |
| max_new_nodes | int | 否 | 最多新增节点数，默认10 |

**请求示例**:

```json
{
  "node_id": "entropy_xinxilun",
  "disciplines": ["计算机", "数学"],
  "max_new_nodes": 10
}
```

**成功响应** (200):

```json
{
  "status": "success",
  "request_id": "req_def456ghi789",
  "data": {
    "new_nodes": [
      {
        "id": "kl_divergence_jisuanji",
        "label": "KL散度",
        "discipline": "计算机",
        "definition": "衡量两个概率分布之间差异的非对称度量",
        "credibility": 0.87
      }
    ],
    "new_edges": [
      {
        "source": "entropy_xinxilun",
        "target": "kl_divergence_jisuanji",
        "relation": "is_foundation_of",
        "weight": 0.83,
        "reasoning": "KL散度基于香农熵定义"
      }
    ],
    "metadata": {
      "parent_node_id": "entropy_xinxilun",
      "expansion_depth": 1
    }
  }
}
```

---

## 三、数据模型

### 3.1 ConceptNode（概念节点）

```typescript
interface ConceptNode {
  id: string;              // 唯一标识，格式: {概念名}_{学科拼音}
  label: string;           // 概念名称
  discipline: string;      // 所属学科
  definition: string;      // 简短定义，最多200字符
  credibility: number;     // 可信度，范围[0.0-1.0]
  metadata?: object;       // 额外元数据（可选）
}
```

### 3.2 ConceptEdge（概念关系边）

```typescript
interface ConceptEdge {
  source: string;          // 源节点ID
  target: string;          // 目标节点ID
  relation: string;        // 关系类型（见3.4）
  weight: number;          // 关联强度，范围[0.0-1.0]
  reasoning: string;       // 关联原因，最多500字符
}
```

### 3.3 Metadata（元数据）

```typescript
interface Metadata {
  total_nodes: number;     // 总节点数
  total_edges: number;     // 总边数
  verified_nodes: number;  // 通过验证的节点数
  avg_credibility: number; // 平均可信度
  processing_time: number; // 处理耗时（秒）
}
```

### 3.4 关系类型枚举

```typescript
type RelationType =
  | "is_foundation_of"   // A是B的理论基础
  | "similar_to"         // A和B在原理上相似
  | "applied_in"         // A应用于B领域
  | "generalizes"        // A是B的泛化
  | "derived_from";      // A由B推导而来
```

## 四、错误码定义

| 错误码 | 说明 | HTTP状态码 |
|--------|------|-----------|
| ERR_1001 | 请求参数无效 | 400 |
| ERR_1002 | 数据验证失败 | 400 |
| ERR_1003 | 请求超时 | 408 |
| ERR_2001 | LLM调用失败 | 500 |
| ERR_2002 | LLM超时 | 504 |
| ERR_2004 | 验证失败 | 500 |
| ERR_2005 | 未找到相关概念 | 404 |
| ERR_2006 | 可信度过低 | 422 |
| ERR_4001 | 概念不存在 | 404 |
| ERR_4002 | 无效的学科类别 | 400 |

## 五、使用示例

### 5.1 Python客户端

```python
import requests

# 概念挖掘
response = requests.post(
    "http://localhost:8000/api/v1/agent/discover",
    json={
        "concept": "熵",
        "disciplines": ["数学", "物理", "信息论"],
        "depth": 2,
        "max_concepts": 20
    },
    timeout=60
)

if response.status_code == 200:
    data = response.json()
    nodes = data["data"]["nodes"]
    edges = data["data"]["edges"]
    print(f"发现 {len(nodes)} 个节点, {len(edges)} 条边")
else:
    error = response.json()
    print(f"错误: {error['message']}")
```

### 5.2 JavaScript客户端

```javascript
// 概念挖掘
const response = await fetch('http://localhost:8000/api/v1/agent/discover', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    concept: '熵',
    disciplines: ['数学', '物理', '信息论'],
    depth: 2,
    max_concepts: 20
  })
});

const data = await response.json();

if (data.status === 'success') {
  const { nodes, edges, metadata } = data.data;
  console.log(`发现 ${nodes.length} 个节点, ${edges.length} 条边`);
  console.log(`平均可信度: ${metadata.avg_credibility}`);
} else {
  console.error(`错误: ${data.message}`);
}
```

## 六、性能指标

| 指标 | 目标值 |
|------|--------|
| 响应时间 | < 15秒（普通概念）< 30秒（复杂概念） |
| 成功率 | > 95% |
| 平均可信度 | > 0.7 |
| 概念覆盖率 | 每个学科至少1个概念 |

## 七、调用流程

```
客户端
  ↓ POST /api/v1/agent/discover
后端API Gateway
  ↓ 转发请求
AgentOrchestrator
  ↓ 编排三个Agent
  ├─ ConceptDiscoveryAgent（10-40%进度）
  ├─ VerificationAgent（50-70%进度）
  └─ GraphBuilderAgent（80-90%进度）
  ↓ 返回响应
客户端接收JSON数据
```

## 八、测试接口

### 8.1 健康检查

**URL**: `GET /api/v1/agent/health`

**响应**:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-16T10:30:00Z",
  "llm_available": true
}
```

### 8.2 Mock数据

开发阶段可以使用`tests/mock_data.py`中的Mock数据进行测试。

## 九、注意事项

1. **超时处理**：客户端应设置60秒超时
2. **幂等性**：相同输入返回相同结果（除非LLM行为变化）
3. **并发限制**：建议限制并发请求数，避免LLM API配额耗尽
4. **缓存策略**：后端可以缓存热门概念的结果
5. **进度推送**：通过WebSocket实时推送处理进度（可选）

## 十、更新日志

### v1.0.0 (2026-01-16)
- 初始版本
- 实现概念挖掘、验证、扩展三个接口
- 支持CoT推理和知识校验
