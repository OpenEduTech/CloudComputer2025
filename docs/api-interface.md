# ConceptGraph AI - API接口文档

## 📋 目录

- [接口概览](#接口概览)
- [通用说明](#通用说明)
- [接口详情](#接口详情)
  - [1. 概念挖掘接口](#1-概念挖掘接口)
  - [2. 概念验证接口](#2-概念验证接口)
  - [3. 图谱扩展接口](#3-图谱扩展接口)
  - [4. 辅助接口](#4-辅助接口)
- [数据模型](#数据模型)
- [错误码](#错误码)
- [使用示例](#使用示例)

---

## 接口概览

| 接口名称 | HTTP方法 | 路径 | 功能描述 |
|---------|---------|------|---------|
| 概念挖掘 | POST | `/api/v1/agent/discover` | 自动发现跨学科相关概念 |
| 概念验证 | POST | `/api/v1/agent/verify` | 验证概念关联的准确性 |
| 图谱扩展 | POST | `/api/v1/agent/expand` | 扩展现有图谱节点 |
| 学科列表 | GET | `/api/v1/agent/disciplines` | 获取支持的学科 |
| 关系类型 | GET | `/api/v1/agent/relations` | 获取关系类型 |

**基础URL**: `http://localhost:8000`  
**API版本**: `v1`

---

## 通用说明

### 认证方式
当前版本无需认证（后续版本将支持API Key）

### 请求头
```http
Content-Type: application/json
Accept: application/json
```

### 响应格式
所有接口均返回JSON格式，基本结构：

**成功响应**:
```json
{
  "status": "success",
  "request_id": "req_20260117_123456",
  "data": { ... }
}
```

**错误响应**:
```json
{
  "status": "error",
  "error_code": "ERR_2001",
  "message": "大模型调用失败，请稍后重试",
  "details": "Connection timeout"
}
```

### 超时时间
- 概念挖掘: 60秒
- 概念验证: 30秒
- 图谱扩展: 45秒

---

## 接口详情

### 1. 概念挖掘接口

#### 基本信息
- **URL**: `/api/v1/agent/discover`
- **方法**: `POST`
- **功能**: 在多个学科领域自动发现与核心概念相关的跨学科概念
- **超时**: 60秒

#### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|-------|------|------|--------|------|
| concept | string | 是 | - | 核心概念词，1-50字符 |
| disciplines | string[] | 否 | 全部学科 | 目标学科列表 |
| depth | integer | 否 | 2 | 挖掘深度，范围[1-3] |
| max_concepts | integer | 否 | 30 | 最大概念数，范围[10-100] |
| enable_verification | boolean | 否 | true | 是否启用知识校验 |

**支持的学科**:
- `"数学"`, `"物理"`, `"化学"`, `"生物"`, `"计算机"`, `"社会学"`

#### 请求示例

```json
POST /api/v1/agent/discover
Content-Type: application/json

{
  "concept": "熵",
  "disciplines": ["数学", "物理", "信息论", "机器学习"],
  "depth": 2,
  "max_concepts": 30,
  "enable_verification": true
}
```

#### 响应示例

```json
{
  "status": "success",
  "request_id": "req_20260117_123456",
  "data": {
    "nodes": [
      {
        "id": "entropy_xinxilun",
        "label": "熵",
        "discipline": "信息论",
        "definition": "信息的不确定性度量",
        "credibility": 0.95,
        "metadata": {
          "source": "Wikipedia",
          "verified": true
        }
      },
      {
        "id": "shannon_entropy_xinxilun",
        "label": "香农熵",
        "discipline": "信息论",
        "definition": "离散随机变量的平均信息量",
        "credibility": 0.92,
        "metadata": {
          "source": "Wikipedia",
          "verified": true
        }
      }
    ],
    "edges": [
      {
        "source": "entropy_xinxilun",
        "target": "shannon_entropy_xinxilun",
        "relation": "is_foundation_of",
        "weight": 0.92,
        "reasoning": "香农熵是信息论中熵的具体定义，用于度量信息的不确定性"
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

#### 错误响应

```json
{
  "status": "error",
  "error_code": "ERR_2005",
  "message": "未找到相关概念，请尝试其他关键词"
}
```

---

### 2. 概念验证接口

#### 基本信息
- **URL**: `/api/v1/agent/verify`
- **方法**: `POST`
- **功能**: 验证两个概念之间的关联是否真实可靠
- **超时**: 30秒

#### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|-------|------|------|--------|------|
| concept_a | string | 是 | - | 概念A，1-100字符 |
| concept_b | string | 是 | - | 概念B，1-100字符 |
| claimed_relation | string | 是 | - | 声称的关联描述，1-500字符 |
| strength | float | 否 | 0.5 | 声称的关联强度，范围[0.0-1.0] |

#### 请求示例

```json
POST /api/v1/agent/verify
Content-Type: application/json

{
  "concept_a": "熵",
  "concept_b": "信息增益",
  "claimed_relation": "信息增益基于熵的概念，用于度量信息的期望减少量",
  "strength": 0.8
}
```

#### 响应示例

```json
{
  "status": "success",
  "request_id": "req_20260117_123457",
  "data": {
    "credibility_score": 0.87,
    "is_valid": true,
    "evidence": [
      {
        "source": "Wikipedia",
        "url": "https://zh.wikipedia.org/wiki/信息增益",
        "snippet": "信息增益是决策树学习中的一个重要概念，基于熵来度量..."
      },
      {
        "source": "Arxiv",
        "url": "https://arxiv.org/abs/1234.5678",
        "snippet": "Information gain is calculated using entropy..."
      }
    ],
    "warnings": []
  }
}
```

#### 错误响应

```json
{
  "status": "error",
  "error_code": "ERR_2006",
  "message": "生成的关联可信度过低，已过滤"
}
```

---

### 3. 图谱扩展接口

#### 基本信息
- **URL**: `/api/v1/agent/expand`
- **方法**: `POST`
- **功能**: 扩展现有图谱中的指定节点，发现更多相关概念
- **超时**: 45秒

#### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|-------|------|------|--------|------|
| node_id | string | 是 | - | 要扩展的节点ID |
| existing_graph | object | 是 | - | 现有图谱数据 |
| disciplines | string[] | 否 | null | 限定扩展的学科 |
| max_new_nodes | integer | 否 | 10 | 最多新增节点数，范围[1-50] |

#### 请求示例

```json
POST /api/v1/agent/expand
Content-Type: application/json

{
  "node_id": "entropy_xinxilun",
  "existing_graph": {
    "nodes": [
      {
        "id": "entropy_xinxilun",
        "label": "熵",
        "discipline": "信息论",
        "definition": "信息的不确定性度量",
        "credibility": 0.95
      }
    ],
    "edges": []
  },
  "disciplines": ["计算机", "数学"],
  "max_new_nodes": 10
}
```

#### 响应示例

```json
{
  "status": "success",
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
        "id": "cross_entropy_jisuanji",
        "label": "交叉熵",
        "discipline": "计算机",
        "definition": "衡量两个概率分布的差异",
        "credibility": 0.88
      }
    ],
    "edges": [
      {
        "source": "entropy_xinxilun",
        "target": "cross_entropy_jisuanji",
        "relation": "derived_from",
        "weight": 0.85,
        "reasoning": "交叉熵是熵概念在机器学习中的应用"
      }
    ],
    "metadata": {
      "parent_node_id": "entropy_xinxilun",
      "new_nodes_count": 8,
      "expansion_depth": 1
    }
  }
}
```

---

### 4. 辅助接口

#### 4.1 获取支持的学科列表

```http
GET /api/v1/agent/disciplines
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "disciplines": ["数学", "物理", "化学", "生物", "计算机", "社会学"],
    "colors": {
      "数学": "#FF6B6B",
      "物理": "#4ECDC4",
      "化学": "#95E1D3",
      "生物": "#F38181",
      "计算机": "#AA96DA",
      "社会学": "#FCBAD3"
    }
  }
}
```

#### 4.2 获取关系类型列表

```http
GET /api/v1/agent/relations
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "types": [
      "is_foundation_of",
      "similar_to",
      "applied_in",
      "generalizes",
      "derived_from"
    ],
    "descriptions": {
      "is_foundation_of": "是...的理论基础",
      "similar_to": "与...在原理上相似",
      "applied_in": "应用于...领域",
      "generalizes": "是...的泛化",
      "derived_from": "由...推导而来"
    }
  }
}
```

---

## 数据模型

### ConceptNode（概念节点）

```typescript
interface ConceptNode {
  id: string;              // 唯一标识，格式: {概念名}_{学科拼音}
  label: string;           // 概念名称
  discipline: string;      // 所属学科
  definition: string;      // 简短定义，最多200字符
  credibility: number;     // 可信度分数，范围[0.0-1.0]
  metadata?: {             // 额外元数据（可选）
    source?: string;       // 数据来源
    verified?: boolean;    // 是否已验证
    [key: string]: any;
  };
}
```

### ConceptEdge（概念关系边）

```typescript
interface ConceptEdge {
  source: string;          // 源节点ID
  target: string;          // 目标节点ID
  relation: string;        // 关系类型
  weight: number;          // 关联强度，范围[0.0-1.0]
  reasoning: string;       // 关联原因，最多500字符
}
```

### GraphData（图谱数据）

```typescript
interface GraphData {
  nodes: ConceptNode[];    // 节点列表
  edges: ConceptEdge[];    // 边列表
  metadata: {
    total_nodes: number;         // 总节点数
    total_edges: number;         // 总边数
    verified_nodes: number;      // 通过验证的节点数
    avg_credibility: number;     // 平均可信度
    processing_time: number;     // 处理耗时（秒）
  };
}
```

---

## 错误码

| 错误码 | 说明 | HTTP状态码 |
|-------|------|-----------|
| ERR_1001 | 请求参数无效 | 400 |
| ERR_1002 | 数据验证失败 | 400 |
| ERR_1003 | 请求超时 | 408 |
| ERR_2001 | 大模型调用失败 | 500 |
| ERR_2004 | 概念验证失败 | 400 |
| ERR_2005 | 未找到相关概念 | 404 |
| ERR_2006 | 可信度过低 | 400 |
| ERR_4001 | 概念不存在 | 404 |
| ERR_4002 | 无效的学科类别 | 400 |

---

## 使用示例

### Python示例

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 概念挖掘
response = requests.post(
    f"{BASE_URL}/agent/discover",
    json={
        "concept": "熵",
        "disciplines": ["数学", "物理", "信息论"],
        "depth": 2,
        "max_concepts": 30
    }
)
graph_data = response.json()

# 2. 概念验证
response = requests.post(
    f"{BASE_URL}/agent/verify",
    json={
        "concept_a": "熵",
        "concept_b": "信息增益",
        "claimed_relation": "信息增益基于熵的概念"
    }
)
verify_result = response.json()

# 3. 图谱扩展
response = requests.post(
    f"{BASE_URL}/agent/expand",
    json={
        "node_id": "entropy_xinxilun",
        "existing_graph": graph_data["data"],
        "max_new_nodes": 10
    }
)
expanded_graph = response.json()
```

### JavaScript示例

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';

// 1. 概念挖掘
const discoverConcepts = async () => {
  const response = await fetch(`${BASE_URL}/agent/discover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      concept: '熵',
      disciplines: ['数学', '物理', '信息论'],
      depth: 2,
      max_concepts: 30
    })
  });
  return await response.json();
};

// 2. 概念验证
const verifyConcept = async () => {
  const response = await fetch(`${BASE_URL}/agent/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      concept_a: '熵',
      concept_b: '信息增益',
      claimed_relation: '信息增益基于熵的概念'
    })
  });
  return await response.json();
};
```

### cURL示例

```bash
# 1. 概念挖掘
curl -X POST "http://localhost:8000/api/v1/agent/discover" \
  -H "Content-Type: application/json" \
  -d '{
    "concept": "熵",
    "disciplines": ["数学", "物理", "信息论"],
    "depth": 2,
    "max_concepts": 30
  }'

# 2. 概念验证
curl -X POST "http://localhost:8000/api/v1/agent/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "concept_a": "熵",
    "concept_b": "信息增益",
    "claimed_relation": "信息增益基于熵的概念"
  }'

# 3. 获取学科列表
curl -X GET "http://localhost:8000/api/v1/agent/disciplines"
```

---

## 启动服务

### 方式1：直接运行

```bash
# 设置环境变量
export OPENAI_API_KEY="sk-xxx"
export OPENROUTER_API_KEY="sk-or-v1-xxx"
export PYTHONPATH="D:\yunjisuanfinal"

# 启动服务
cd api
python main.py
```

### 方式2：使用uvicorn

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

---

## 注意事项

1. **API Key配置**：确保在环境变量中配置了OpenAI和OpenRouter的API Key
2. **超时处理**：复杂查询可能需要较长时间，建议客户端设置合理的超时时间
3. **并发限制**：当前版本未设置并发限制，生产环境建议添加限流
4. **缓存策略**：相同查询建议客户端缓存结果，减少重复请求
5. **错误重试**：遇到5xx错误时，建议客户端实现指数退避重试策略

---

## 更新日志

### v1.0.0 (2026-01-17)
- ✅ 初始版本发布
- ✅ 实现概念挖掘接口
- ✅ 实现概念验证接口
- ✅ 实现图谱扩展接口
- ✅ 添加辅助查询接口
- ✅ 完整的错误处理和日志
