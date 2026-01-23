# Prompt 工程文档

## 1. 概述

本文档详细说明了跨学科知识图谱智能体的 Prompt 设计策略、工具链和校验机制。系统采用多阶段 Prompt 工程，结合严格的校验层，确保生成的知识图谱准确可靠。

## 2. Prompt 设计原则

### 2.1 核心原则

1. **明确性**: 清晰定义任务目标和输出格式
2. **结构化**: 使用 JSON 格式确保输出可解析
3. **约束性**: 明确限制条件，避免发散
4. **可验证性**: 输出包含可验证的信息
5. **防幻觉**: 强调只输出确定性强的内容

### 2.2 设计模式

采用**多阶段渐进式**Prompt 策略：

```
阶段1: 概念识别 (低温度, 高确定性)
    ↓
阶段2: 跨学科挖掘 (中温度, 创造性)
    ↓
阶段3: 关系验证 (低温度, 严格验证)
    ↓
阶段4: 反向验证 (低温度, 双向确认)
```

## 3. 多阶段 Prompt 详解

### 3.1 阶段 1: 概念识别

**目标**: 识别输入概念的基本信息和学科归属

**Prompt 模板**:

```
你是一个跨学科知识专家。

任务：分析给定概念的学科归属和基本含义。

输入概念：{concept}

请按以下JSON格式输出：
{
    "concept": "概念名称",
    "primary_domain": "主要学科领域",
    "definition": "简短定义（50字以内）",
    "keywords": ["关键词1", "关键词2", "关键词3"]
}

要求：
1. 准确识别概念的主要学科归属
2. 定义要简洁准确
3. 提取3-5个关键词

只输出JSON，不要其他内容。
```

**参数设置**:

- Temperature: 0.3 (低温度，确保准确性)
- Max Tokens: 500

**示例输入**: "熵"

**示例输出**:

```json
{
  "concept": "熵",
  "primary_domain": "物理学",
  "definition": "衡量系统无序程度或不确定性的物理量",
  "keywords": ["热力学", "信息论", "无序度", "统计力学"]
}
```

**设计要点**:

- 使用低温度确保输出稳定
- 限制定义长度避免冗长
- 关键词用于后续关联挖掘

### 3.2 阶段 2: 跨学科关联挖掘

**目标**: 在多个学科中发现与核心概念的关联

**Prompt 模板**:

```
你是一个跨学科知识专家，擅长发现不同学科间的概念关联。

核心概念：{concept}
主要学科：{primary_domain}
概念定义：{definition}

任务：在以下5个学科领域中，寻找与该概念相关的概念：
1. 数学 (Mathematics)
2. 物理学 (Physics)
3. 计算机科学 (Computer Science)
4. 生物学 (Biology)
5. 社会学 (Sociology)

对于每个学科，找出1-3个相关概念，并说明关系。

输出JSON格式：
{
    "relations": [
        {
            "source_concept": "原概念",
            "target_concept": "相关概念名称",
            "target_domain": "目标学科",
            "relation_type": "关系类型（如：类比、应用、理论基础、启发、数学建模等）",
            "relation_strength": 8,
            "explanation": "关系说明（100字以内）"
        }
    ]
}

要求：
1. relation_strength范围1-10，表示关系强度
2. 只输出确定性强的关联，不要臆测
3. 每个学科至少找1个相关概念
4. 关系类型要准确，explanation要有说服力
5. 总共输出5-15个关系

只输出JSON，不要其他内容。
```

**参数设置**:

- Temperature: 0.7 (中等温度，平衡创造性和准确性)
- Max Tokens: 2000

**示例输入**: 概念="熵", 学科="物理学"

**示例输出**:

```json
{
  "relations": [
    {
      "source_concept": "熵",
      "target_concept": "香农熵",
      "target_domain": "计算机科学",
      "relation_type": "类比应用",
      "relation_strength": 9,
      "explanation": "香农将热力学熵的概念引入信息论，用于衡量信息的不确定性，两者在数学形式上高度相似"
    },
    {
      "source_concept": "熵",
      "target_concept": "遗传多样性",
      "target_domain": "生物学",
      "relation_type": "概念类比",
      "relation_strength": 7,
      "explanation": "生态系统的遗传多样性可以用熵的概念来量化，多样性越高，系统的'熵'越大"
    },
    {
      "source_concept": "熵",
      "target_concept": "社会无序度",
      "target_domain": "社会学",
      "relation_type": "隐喻应用",
      "relation_strength": 6,
      "explanation": "社会学中借用熵的概念描述社会系统的混乱程度和不确定性"
    }
  ]
}
```

**设计要点**:

- 明确指定 5 个学科领域，确保跨学科覆盖
- 要求说明关系类型和强度，便于后续验证
- 限制 explanation 长度，避免冗长
- 强调"只输出确定性强的关联"，防止幻觉

### 3.3 阶段 3: 关系验证

**目标**: 验证挖掘出的关系是否合理

**Prompt 模板**:

```
你是一个严谨的知识验证专家。

请验证以下概念关系是否合理：

源概念：{source_concept} (学科: {source_domain})
目标概念：{target_concept} (学科: {target_domain})
关系类型：{relation_type}
关系说明：{explanation}

请评估：
1. 这个关系是否真实存在？
2. 关系说明是否准确？
3. 关系强度是否合理？

输出JSON格式：
{
    "valid": true,
    "confidence": 0.85,
    "reason": "验证理由",
    "suggested_strength": 8
}

要求：
1. valid: true/false，表示关系是否有效
2. confidence: 0-1之间的浮点数，表示置信度
3. reason: 简短说明验证理由
4. suggested_strength: 建议的关系强度(1-10)

只输出JSON，不要其他内容。
```

**参数设置**:

- Temperature: 0.3 (低温度，严格验证)
- Max Tokens: 500

**示例输入**:

```
源概念: 熵 (物理学)
目标概念: 香农熵 (计算机科学)
关系类型: 类比应用
关系说明: 香农将热力学熵的概念引入信息论...
```

**示例输出**:

```json
{
  "valid": true,
  "confidence": 0.95,
  "reason": "香农熵确实是从热力学熵类比而来，两者在数学形式上高度相似，这是信息论的重要基础",
  "suggested_strength": 9
}
```

### 3.4 阶段 4: 反向验证

**目标**: 从目标概念反向验证关系

**Prompt 模板**:

```
你是一个知识验证专家。

已知关系：
从 {source_concept} ({source_domain}) 到 {target_concept} ({target_domain})
关系类型：{relation_type}

现在请从反向角度验证：
从 {target_concept} 的角度看，它与 {source_concept} 是否确实存在 {relation_type} 关系？

输出JSON格式：
{
    "reverse_valid": true,
    "confidence": 0.9,
    "reason": "反向验证理由"
}

只输出JSON，不要其他内容。
```

**参数设置**:

- Temperature: 0.3
- Max Tokens: 500

**设计要点**:

- 反向验证确保关系的双向一致性
- 防止单向臆测的关系

## 4. 校验层 (Check Layer)

### 4.1 三重校验机制

```python
class ValidationLayer:
    def validate_relation(self, relation):
        # 1. 直接验证
        direct = self.direct_validation(relation)

        # 2. 反向验证
        reverse = self.reverse_validation(relation)

        # 3. 综合判断
        is_valid = (
            direct.valid and
            direct.confidence >= 0.6 and
            reverse.valid and
            reverse.confidence >= 0.6
        )

        return is_valid
```

### 4.2 置信度计算

```python
final_confidence = (
    direct_confidence * 0.6 +  # 直接验证权重60%
    reverse_confidence * 0.4    # 反向验证权重40%
)
```

### 4.3 一致性检查

对于关键决策，使用多次采样验证一致性：

```python
async def check_consistency(self, prompt, n=3):
    responses = await self.llm_client.call_llm_multiple(
        prompt=prompt,
        n=n,
        temperature=0.7
    )

    consistency_score = calculate_consistency(responses)

    return consistency_score >= 0.7
```

## 5. 系统提示词 (System Prompt)

所有阶段共用的系统提示词：

```
你是一个专业的跨学科知识专家，具有以下特点：

1. 知识广博：精通数学、物理、计算机科学、生物学、社会学等多个学科
2. 思维严谨：只陈述确定性强的知识，不进行臆测
3. 善于类比：能够发现不同学科间的深层联系
4. 输出规范：严格按照JSON格式输出，不添加额外内容

你的任务是帮助用户构建跨学科知识图谱，发现概念间的"远亲"关系。
```

## 6. 工具链

### 6.1 LLM 客户端

```python
class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=...)
        self.model = "gpt-4"

    async def call_llm_json(self, prompt, system_prompt, temperature):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )

        return parse_json(response)
```

### 6.2 重试机制

使用 tenacity 库实现自动重试：

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_llm(self, prompt):
    # LLM调用逻辑
    pass
```

### 6.3 错误处理

```python
try:
    result = await llm_client.call_llm_json(prompt)
except json.JSONDecodeError:
    # 尝试提取JSON
    result = extract_json_from_text(response_text)
except Exception as e:
    logger.error(f"LLM call failed: {e}")
    raise
```

## 7. 推理链路 (Chain of Thought)

### 7.1 完整推理流程

```
用户输入: "神经网络"
    ↓
[CoT Step 1] 概念识别
    → 识别为"计算机科学"领域
    → 定义: "模拟生物神经系统的计算模型"
    ↓
[CoT Step 2] 跨学科挖掘
    → 数学: 矩阵运算、梯度下降
    → 物理: 能量最小化
    → 生物: 生物神经元
    → 社会学: 集体智能
    ↓
[CoT Step 3] 关系验证
    → 验证每个关系的合理性
    → 过滤低置信度关系
    ↓
[CoT Step 4] 图谱构建
    → 构建节点和边
    → 存储到Neo4j
```

### 7.2 思维链提示

在 Prompt 中嵌入思维链引导：

```
请按以下步骤思考：
1. 首先，理解核心概念的本质
2. 然后，在每个学科中寻找相似的概念或应用
3. 接着，分析这些概念之间的关系类型
4. 最后，评估关系的强度和可靠性
```

## 8. 防止幻觉的策略

### 8.1 明确约束

- "只输出确定性强的关联，不要臆测"
- "如果不确定，宁可不输出"
- "关系说明要有具体依据"

### 8.2 低温度采样

- 验证阶段使用 temperature=0.3
- 减少随机性，提高确定性

### 8.3 多重验证

- 直接验证 + 反向验证
- 一致性检查
- 置信度阈值过滤

### 8.4 结构化输出

- 强制 JSON 格式
- 包含置信度字段
- 要求提供理由

## 9. 性能优化

### 9.1 并发调用

```python
# 并发验证多个关系
tasks = [validate_relation(r) for r in relations]
results = await asyncio.gather(*tasks)
```

### 9.2 缓存策略

- 缓存已验证的关系
- 避免重复 LLM 调用

### 9.3 批处理

- 批量处理关系验证
- 减少 API 调用次数

## 10. 示例：完整流程

### 输入

```
概念: "熵"
```

### 输出

```json
{
  "concept_info": {
    "concept": "熵",
    "primary_domain": "物理学",
    "definition": "衡量系统无序程度的物理量"
  },
  "relations": [
    {
      "source": "熵",
      "target": "香农熵",
      "domain": "计算机科学",
      "type": "类比应用",
      "strength": 9,
      "confidence": 0.95
    },
    {
      "source": "熵",
      "target": "遗传多样性",
      "domain": "生物学",
      "type": "概念类比",
      "strength": 7,
      "confidence": 0.85
    }
  ]
}
```

## 11. 最佳实践

1. **迭代优化**: 根据实际效果不断调整 Prompt
2. **A/B 测试**: 对比不同 Prompt 版本的效果
3. **人工审核**: 定期人工审核生成结果
4. **用户反馈**: 收集用户反馈改进 Prompt
5. **版本管理**: 对 Prompt 进行版本控制

## 12. 常见问题

### Q1: 如何处理 LLM 返回格式错误？

A: 实现容错解析逻辑，尝试提取 JSON：

````python
def extract_json(text):
    # 移除markdown代码块
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())
````

### Q2: 如何提高关系的准确性？

A:

1. 降低 temperature
2. 增加验证步骤
3. 提高置信度阈值
4. 使用更强的模型（如 GPT-4）

### Q3: 如何处理不同语言？

A: 在 Prompt 中明确指定输出语言，或使用多语言模型。


