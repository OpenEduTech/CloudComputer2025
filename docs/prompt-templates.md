# Prompt模板说明

## 一、概述

ConceptGraph AI使用精心设计的Prompt模板，结合**Chain-of-Thought (CoT)推理**，确保跨学科知识挖掘的质量。

## 二、Prompt设计原则

### 2.1 核心原则

1. **明确推理步骤**：要求LLM逐步思考，避免直接输出
2. **结构化输出**：严格定义JSON格式
3. **评分标准**：提供可信度/强度的量化标准
4. **示例引导**：提供高质量的Few-shot示例
5. **约束条件**：明确输出数量、格式、内容限制

### 2.2 CoT推理优势

- 减少幻觉：明确推理过程更易验证
- 提高质量：逐步推理比一步到位更准确
- 可解释性：用户可以看到推理逻辑

## 三、DiscoveryPrompt（概念挖掘Prompt）

### 3.1 核心模板

```python
【步骤1：概念本质分析】
核心概念：{concept}
请回答：
1. 这个概念的核心定义是什么？
2. 它的数学/物理本质是什么？
3. 它解决了什么根本问题？

【步骤2：跨学科映射】
在以下学科中寻找相关概念：{disciplines}
对于每个学科，请思考：
- 该学科中是否有类似的概念或原理？
- 底层机制是否相通？
- 是否存在历史上的类比或启发关系？

【步骤3：关联强度量化】
根据以下标准评分（0-1）：
- 0.8-1.0：底层数学/物理原理完全相同
- 0.5-0.8：存在明确的类比关系或理论桥梁
- 0.2-0.5：概念间接相关，需要多步推理
- 0.0-0.2：几乎无关或牵强附会
```

### 3.2 输出格式要求

```json
[
  {
    "discipline": "学科名称",
    "concept_name": "相关概念名称",
    "definition": "概念定义（不超过100字）",
    "reasoning": "详细的推理过程（100-300字）",
    "common_principle": "共同的底层原理",
    "relation_type": "关系类型",
    "strength": 0.85
  }
]
```

### 3.3 关键技巧

1. **强制学科覆盖**：要求每个学科至少返回1个概念
2. **深层原理优先**：避免表面文字联系
3. **强度阈值**：明确说明低于0.2是牵强附会

### 3.4 示例Prompt

**输入**：熵

**Prompt片段**：
```
【步骤1：概念本质分析】
核心概念：熵

请回答：
1. 这个概念的核心定义是什么？
   → 熵是对系统无序程度或不确定性的度量

2. 它的数学/物理本质是什么？
   → 概率分布的期望对数：H = -Σ p(x)log p(x)

3. 它解决了什么根本问题？
   → 量化信息量、混乱度、能量可用性
```

## 四、VerificationPrompt（知识校验Prompt）

### 4.1 核心模板

```python
【待验证的关联】
概念A：{concept_a}
概念B：{concept_b}
声称的关联：{claimed_relation}

【验证步骤】
1. 定义核查
   - 查阅权威来源确认两个概念的标准定义
   - 检查定义中是否提到彼此或共同原理

2. 文献支持
   - 搜索是否有学术论文明确提到这种关联
   - 统计支持文献的数量和权威性

3. 逻辑一致性
   - 判断该关联在逻辑上是否成立
   - 是否存在反例或矛盾
```

### 4.2 可信度评分标准

```
- 0.9-1.0：学术界公认，有教材级支持
- 0.7-0.9：有多篇高质量论文支持
- 0.5-0.7：有一定依据但不充分
- 0.3-0.5：逻辑上成立但缺乏文献支持
- 0.0-0.3：可能错误或过度类比
```

### 4.3 输出格式

```json
{
  "credibility_score": 0.87,
  "is_valid": true,
  "evidence": [
    {
      "source": "Wikipedia",
      "url": "https://...",
      "snippet": "具体段落引用（不超过200字）"
    }
  ],
  "logical_reasoning": "详细的逻辑分析（200-400字）",
  "warnings": []
}
```

### 4.4 关键原则

1. **宁可严格，不可放松**：低于0.5标记为"待验证"
2. **证据必需**：至少1个evidence，否则分数不超过0.4
3. **明确警告**：问题在warnings中说明

## 五、GraphPrompt（图谱构建Prompt）

### 5.1 核心任务

```python
【任务要求】
1. 提取节点信息：
   - id：唯一标识符（格式：概念名拼音_学科拼音）
   - label：概念名称
   - discipline：所属学科
   - definition：简短定义（1句话）
   - credibility：可信度分数

2. 提取边信息：
   - source/target：节点ID
   - relation：关系类型
   - weight：关联强度
   - reasoning：关联原因
```

### 5.2 关系类型定义

```python
- "is_foundation_of"：A是B的理论基础
- "similar_to"：A和B在原理上相似
- "applied_in"：A应用于B领域
- "generalizes"：A是B的泛化
- "derived_from"：A由B推导而来
```

### 5.3 输出格式

```json
{
  "nodes": [...],
  "edges": [...],
  "metadata": {
    "total_nodes": 18,
    "total_edges": 24,
    "avg_credibility": 0.87
  }
}
```

### 5.4 数据完整性检查

```python
【重要规则】
1. 节点ID必须唯一，使用小写字母和下划线
2. 所有边的source和target必须对应存在的节点ID
3. 关系类型必须从预定义的5种中选择
4. credibility和weight必须在[0.0, 1.0]范围内
5. 确保JSON格式严格有效
```

## 六、Prompt优化技巧

### 6.1 温度参数

```python
discovery:   temperature=0.3  # 保持创造性但不过度发散
verification: temperature=0.2  # 严格验证，减少随机性
graph_builder: temperature=0.1  # 格式化任务，确保一致性
```

### 6.2 Token限制

```python
discovery:   max_tokens=2000  # 需要详细推理
verification: max_tokens=1500  # 验证结果相对简洁
graph_builder: max_tokens=2000  # 大量JSON输出
```

### 6.3 System Role设置

```python
discovery_system_role = "你是一个跨学科知识专家，擅长发现不同领域之间的深层联系。"
verification_system_role = "你是一个严谨的知识验证专家，负责核查信息的准确性。"
graph_system_role = "你是一个图数据结构专家，擅长将知识转换为标准化的图结构。"
```

## 七、Few-shot示例

### 7.1 示例价值

- 提供标准输出格式
- 展示高质量推理过程
- 引导LLM模仿示例风格

### 7.2 示例内容

```python
【示例：分析"熵"概念】

步骤1 - 概念本质分析：
- 核心定义：熵是对系统无序程度或不确定性的度量
- 数学本质：概率分布的期望对数
- 根本问题：量化信息量、混乱度、能量可用性

步骤2 - 跨学科映射：
【信息论】
- 相关概念：香农熵、信息增益
- 底层机制：都使用概率分布描述不确定性
- 关联强度：0.95（数学公式完全一致）

【热力学】
- 相关概念：热力学熵、玻尔兹曼熵公式
- 底层机制：都描述微观状态数与宏观状态的关系
- 关联强度：0.92（理论基础）
```

## 八、Prompt迭代优化

### 8.1 常见问题及解决

| 问题 | 解决方案 |
|------|---------|
| 输出格式不正确 | 添加"严格JSON"强调，提供完整示例 |
| 关联过于牵强 | 降低温度参数，明确评分标准 |
| 学科覆盖不均 | 强制要求每个学科至少1个概念 |
| 推理过程简略 | 增加"详细推理"要求，限制字数 |

### 8.2 A/B测试方法

```python
# 测试不同Prompt版本的效果
version_a_prompt = "简单版Prompt"
version_b_prompt = "详细版Prompt"

# 对比输出质量
results_a = await test_prompt(version_a_prompt, test_concepts)
results_b = await test_prompt(version_b_prompt, test_concepts)

# 评估指标：准确率、覆盖率、可信度
```

## 九、多语言支持

### 9.1 中文优先

- 所有Prompt使用中文，确保准确理解
- 学科名称、概念名称使用中文

### 9.2 英文fallback

```python
if chinese_response_failed:
    # 使用英文Prompt重试
    prompt_en = translate_to_english(prompt_zh)
```

## 十、Prompt版本管理

### 10.1 版本控制

```python
# prompts/versions/
discovery_v1.0.py  # 初始版本
discovery_v1.1.py  # 优化评分标准
discovery_v2.0.py  # 引入Few-shot
```

### 10.2 配置文件

```yaml
# prompts/prompt_config.json
{
  "discovery": {
    "version": "2.0",
    "template": "discovery_v2.0",
    "temperature": 0.3
  }
}
```

## 十一、总结

优秀的Prompt设计是Agent质量的关键：

1. **结构化思维**：CoT推理 > 直接输出
2. **严格约束**：明确格式、评分标准、数量限制
3. **持续优化**：通过A/B测试迭代改进
4. **容错处理**：格式错误时引导LLM修复

通过这套Prompt体系，ConceptGraph AI能够稳定输出高质量的跨学科知识图谱。
