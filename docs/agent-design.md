# Agent设计文档

## 一、概述

ConceptGraph AI的智能体系统采用**多Agent协作**模式，包含三个核心Agent：

1. **ConceptDiscoveryAgent** - 概念关联挖掘Agent
2. **VerificationAgent** - 知识校验Agent
3. **GraphBuilderAgent** - 图谱构建Agent

这三个Agent由**AgentOrchestrator**（编排器）统一协调，形成完整的知识图谱构建流水线。

## 二、系统架构

```
用户请求 "熵"
    ↓
AgentOrchestrator（编排器）
    ↓
┌───────────────────────────────────────────────────┐
│  阶段1: ConceptDiscoveryAgent（概念挖掘）          │
│  - 调用LLM进行跨学科推理                            │
│  - 在6个学科中搜索相关概念                          │
│  - 输出：24个候选概念                              │
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│  阶段2: VerificationAgent（知识校验） ⭐           │
│  - 多源验证（Wikipedia、学术论文）                  │
│  - 可信度评分（0-1）                               │
│  - 输出：18个验证通过的概念                         │
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│  阶段3: GraphBuilderAgent（图谱构建）              │
│  - 提取实体（节点）                                │
│  - 提取关系（边）                                  │
│  - 生成JSON（nodes + edges + metadata）            │
└───────────────────────────────────────────────────┘
    ↓
返回图谱数据
```

## 三、核心Agent详解

### 3.1 ConceptDiscoveryAgent（概念关联挖掘Agent）

#### 功能
在多个学科领域发现与核心概念相关的知识。

#### 核心方法

```python
async def discover_concepts(
    concept: str,           # 核心概念
    disciplines: List[str], # 目标学科列表
    depth: int = 2,         # 挖掘深度
    max_concepts: int = 30  # 最大概念数
) -> Dict[str, Any]
```

#### 工作流程

1. **输入验证**：检查概念是否为空，学科是否有效
2. **Prompt生成**：使用`DiscoveryPrompt.get_discovery_prompt()`生成CoT推理Prompt
3. **LLM调用**：调用GPT-4进行跨学科推理
4. **结果解析**：提取概念列表，按关联强度排序
5. **数量限制**：保留Top N个高质量概念

#### 特色功能

- **CoT推理**：明确推理步骤，避免表面关联
- **学科强制覆盖**：确保每个学科都有概念
- **关联强度评分**：基于底层原理相似性

#### 示例输出

```json
{
  "source_concept": "熵",
  "related_concepts": [
    {
      "concept_name": "香农熵",
      "discipline": "信息论",
      "definition": "信息的不确定性度量",
      "reasoning": "都使用概率分布的对数期望...",
      "strength": 0.95
    }
  ],
  "count": 18
}
```

### 3.2 VerificationAgent（知识校验Agent）⭐ 核心创新

#### 功能
验证概念关联的准确性，解决大模型幻觉问题。

#### 核心方法

```python
async def verify_relation(
    concept_a: str,         # 概念A
    concept_b: str,         # 概念B
    claimed_relation: str,  # 声称的关联
    strength: float         # 声称的强度
) -> Dict[str, Any]
```

#### 验证策略

1. **定义核查**：查阅Wikipedia、学术定义
2. **文献支持**：搜索学术论文、教科书
3. **逻辑一致性**：判断是否存在反例
4. **可信度评分**：0-1分数，0.5为阈值

#### 可信度评分标准

| 分数范围 | 说明 | 示例 |
|---------|------|------|
| 0.9-1.0 | 学术界公认，有教材级支持 | 熵 ↔ 香农熵 |
| 0.7-0.9 | 有多篇高质量论文支持 | 神经网络 ↔ 反向传播 |
| 0.5-0.7 | 有一定依据但不充分 | 熵 ↔ 生态多样性 |
| 0.3-0.5 | 逻辑上成立但缺乏文献 | 概念类比 |
| 0.0-0.3 | 可能错误或过度类比 | 牵强附会 |

#### 示例输出

```json
{
  "credibility_score": 0.92,
  "is_valid": true,
  "evidence": [
    {
      "source": "Wikipedia",
      "url": "https://...",
      "snippet": "香农熵是信息论的基本概念..."
    }
  ],
  "warnings": []
}
```

### 3.3 GraphBuilderAgent（图谱构建Agent）

#### 功能
将验证后的概念转换为标准的图数据结构。

#### 核心方法

```python
async def build_graph(
    source_concept: str,
    verified_concepts: List[Dict[str, Any]]
) -> Dict[str, Any]
```

#### 工作流程

1. **节点提取**：生成唯一ID、标签、定义
2. **边提取**：提取关系类型、权重、推理
3. **数据验证**：确保节点ID唯一、边引用有效
4. **元数据计算**：统计节点数、边数、平均可信度

#### 输出格式

```json
{
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
    "avg_credibility": 0.87
  }
}
```

## 四、AgentOrchestrator（编排器）

### 功能
统一协调三个Agent的工作流程。

### 核心方法

```python
async def discover(
    concept: str,
    disciplines: Optional[List[str]] = None,
    depth: int = 2,
    max_concepts: int = 30,
    enable_verification: bool = True,
    progress_tracker: Optional[ProgressTracker] = None
) -> DiscoverResponse
```

### 完整流程

```
1. 输入验证（5%进度）
   ↓
2. 概念挖掘（10-40%进度）
   - ConceptDiscoveryAgent.discover_concepts()
   ↓
3. 知识校验（50-70%进度）
   - VerificationAgent.verify_concepts()
   ↓
4. 图谱构建（80-90%进度）
   - GraphBuilderAgent.build_graph()
   ↓
5. 返回响应（100%进度）
```

## 五、容错设计

### 5.1 LLM调用容错

```python
# 指数退避重试
for attempt in range(MAX_RETRIES):
    try:
        response = await llm_client.call()
        return response
    except Exception:
        await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
```

### 5.2 降级策略

| 失败场景 | 降级方案 |
|---------|---------|
| LLM调用失败 | 使用本地规则库 |
| 验证失败 | 降低可信度但保留概念 |
| 图谱构建失败 | 使用fallback手动构建 |

### 5.3 JSON解析容错

```python
# 尝试提取Markdown代码块
if "```json" in response:
    json_str = response.split("```json")[1].split("```")[0]

# 解析失败时，让LLM修复JSON
fix_prompt = "以下JSON格式有误，请修复..."
```

## 六、性能优化

### 6.1 并发处理

- 批量验证多个概念（`batch_verify()`）
- 异步调用LLM（`asyncio`）

### 6.2 缓存策略（预留接口）

```python
# 后端可以添加Redis缓存
@cache(ttl=3600)
async def discover_concepts(concept):
    # 相同概念1小时内直接返回缓存
    pass
```

## 七、扩展性设计

### 7.1 支持更多学科

```python
# shared/constants.py
class Discipline:
    ECONOMICS = "经济学"
    PSYCHOLOGY = "心理学"
    # 只需添加常量即可
```

### 7.2 支持更多LLM

```python
# agents/llm_client.py
class ClaudeClient(LLMClient):
    # 继承并实现Anthropic API
    pass
```

### 7.3 节点扩展功能

```python
# 点击节点展开子概念
expanded_graph = await orchestrator.expand(
    node_id="entropy_xinxilun",
    existing_graph=current_graph
)
```

## 八、日志与监控

### 日志级别

```python
logger.info(f"[{request_id}] Starting discovery for: {concept}")
logger.warning(f"No concepts found for: {concept}")
logger.error(f"LLM API error: {str(e)}")
```

### 进度追踪

```python
await progress_tracker.update(
    stage="discovering",
    progress=40,
    message="发现 18 个相关概念"
)
```

## 九、测试策略

### 单元测试

```bash
pytest tests/test_agents.py -v
```

### Mock测试

```python
# 使用mock_data.py中的数据
from tests.mock_data import MOCK_DISCOVER_RESPONSE
```

### 集成测试

```python
# 测试完整流程
response = await orchestrator.discover("测试概念")
assert response.status == "success"
```

## 十、未来优化方向

1. **引入RAG**：结合向量数据库进行语义检索
2. **多轮对话**：支持用户反馈和迭代优化
3. **领域专家Agent**：针对特定学科的专家Agent
4. **可视化推理链**：展示CoT推理过程
5. **A/B测试**：对比不同Prompt的效果
