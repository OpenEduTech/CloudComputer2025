# LLM Agent 智能体策略文档

## 目录
1. [智能体设计概述](#智能体设计概述)
2. [核心 Prompt 模板](#核心-prompt-模板)
3. [Agent 设计过程](#agent-设计过程)
4. [工具链](#工具链)
5. [决策流程](#决策流程)
6. [优化策略](#优化策略)

---

## 智能体设计概述

### 智能体定义

**LLMAgent** 是一个多模块协作的智能学习系统，通过组合多个专用的 LLM 引擎和数据处理模块，为用户提供个性化、自适应的学习评估体验。

```
智能体 = LLM引擎 + 工具链 + 决策引擎 + 反馈机制
```

### 核心思想

| 维度 | 设计 | 说明 |
|------|------|------|
| **分工** | 专用 Agent 负责特定任务 | 题目生成、答案评估、弱点分析 |
| **协作** | 主控 Engine 统筹调度 | LLMAgent 协调各子模块 |
| **反馈** | 多维度评估 + 闭环优化 | 用户反馈→模型调整→持续改进 |
| **适应** | 动态难度调整 + 个性化 | 根据用户表现实时调整 |

### 应用场景

1. **学习材料处理**
   - 从文档自动生成题目
   - 适应多种格式输入

2. **题目生成**
   - 多种题型支持
   - 难度智能分配

3. **答案评估**
   - 自动判卷
   - 多维度反馈

4. **学习分析**
   - 弱点识别
   - 个性化建议

---

## 核心 Prompt 模板

### 1. 题目生成 Prompt

#### 1.1 选择题生成

**Prompt 模板**：
```
基于以下学习内容生成一道{difficulty}难度的选择题：

学习内容：
{context}

要求：
1. 问题应该测试对核心概念的理解
2. 提供4个选项，其中一个是正确答案
3. 错误选项应该是有迷惑性的常见误解
4. 提供详细的解释说明为什么正确答案正确，其他选项为什么错误

返回JSON格式：
{
    "question": "问题文本",
    "options": ["选项A", "选项B", "选项C", "选项D"],
    "correct_answer": "正确选项的完整文本",
    "explanation": "详细的解释",
    "tags": ["标签1", "标签2"],
    "difficulty": "{difficulty}"
}
```

**设计要点**：
- ✅ 明确指定难度级别
- ✅ 要求 4 个选项，明确区分
- ✅ 强调干扰项的迷惑性
- ✅ 要求详细解释
- ✅ JSON 结构化输出便于解析

**难度参数**：
- `easy`: 基础概念，直接题目
- `medium`: 应用理解，需要推理
- `hard`: 深度分析，综合应用

**示例输出**：
```json
{
    "question": "Python中哪个关键字用于定义函数？",
    "options": ["function", "def", "func", "define"],
    "correct_answer": "def",
    "explanation": "在Python中，使用'def'关键字定义函数。选项A是JavaScript语法，选项C和D不是有效的Python关键字。",
    "tags": ["Python基础", "函数定义"],
    "difficulty": "easy"
}
```

#### 1.2 简答题生成

**Prompt 模板**：
```
基于以下学习内容生成一道{difficulty}难度的简答题：

学习内容：
{context}

要求：
1. 问题应该测试对概念的理解和应用能力
2. 提供参考答案要点
3. 提供评分标准

返回JSON格式：
{
    "question": "问题文本",
    "reference_answer": "参考答案",
    "scoring_criteria": ["要点1", "要点2", "要点3"],
    "explanation": "题目考察的知识点和解题思路",
    "tags": ["标签1", "标签2"],
    "difficulty": "{difficulty}"
}
```

**设计要点**：
- ✅ 明确评分标准（关键要点）
- ✅ 提供参考答案
- ✅ 阐述知识点
- ✅ 便于评估

**示例输出**：
```json
{
    "question": "请解释什么是面向对象编程（OOP），并举一个生活中的例子。",
    "reference_answer": "面向对象编程是一种编程范式，将程序看作是对象的集合，每个对象有属性和方法。例如：汽车类可以有属性（颜色、品牌）和方法（启动、加速）。",
    "scoring_criteria": [
        "正确解释OOP的基本概念",
        "提供合理的生活例子",
        "理解属性和方法的区别"
    ],
    "explanation": "本题考察对OOP核心概念的理解和实际应用能力。",
    "tags": ["OOP", "编程范式"],
    "difficulty": "medium"
}
```

#### 1.3 真假题生成

**Prompt 模板**：
```
基于以下学习内容生成一道{difficulty}难度的真假题：

学习内容：
{context}

要求：
1. 陈述应该与学习内容直接相关
2. 错误陈述应该是常见的误解
3. 提供详细的解释

返回JSON格式：
{
    "question": "问题陈述（通常以'是'或'否'开头）",
    "correct_answer": "true/false",
    "explanation": "详细解释为什么这个陈述是真还是假",
    "tags": ["标签1", "标签2"],
    "difficulty": "{difficulty}"
}
```

### 2. 答案评估 Prompt - Prometheus 模式

#### 2.1 核心评估 Prompt

**Prompt 模板**（使用 CoT 链式思维）：
```
你是一个公平、客观的评估专家。请评估以下答案：

问题：{question}

参考答案：{reference_answer}

评分标准：
{scoring_criteria}

用户答案：{user_answer}

请按照以下步骤进行（CoT推理）：
1. 分析用户答案是否涵盖了参考答案的关键要点
2. 检查是否有事实性错误
3. 评估答案的完整性和准确性
4. 给出具体的改进建议

请以JSON格式返回评估结果：
{
    "is_correct": true/false,
    "score": 0-100,
    "feedback": "总体反馈",
    "detailed_explanation": "详细解释",
    "suggested_improvement": "改进建议",
    "confidence_score": 0-1,
    "mistakes": ["错误点1", "错误点2"]
}

确保评估公平，避免过于严格或宽松。
```

**设计要点**：

| 方面 | 设计 | 目的 |
|------|------|------|
| **CoT 链式思维** | 分步骤推理 | 增强逻辑性，减少偏差 |
| **关键要点检查** | 覆盖率分析 | 客观评估完整性 |
| **事实性检查** | 错误识别 | 发现明显的事实错误 |
| **置信度** | 0-1 分数 | 表示评估的可靠性 |
| **改进建议** | 具体指导 | 帮助用户学习 |

#### 2.2 Prometheus 评分框架

**核心原理**：
```
Prometheus = Process (流程) + Reasoning (推理) + Metric (指标) + Evidence (证据) + Trust (信任度)
```

**实现维度**：

| 维度 | 说明 | 实现 |
|------|------|------|
| **过程** | 明确的推理步骤 | CoT 链式思维 |
| **推理** | 逻辑清晰的分析 | 多维度评估 |
| **指标** | 量化的评分标准 | 0-100 分数 |
| **证据** | 具体的评价点 | mistakes 列表 |
| **信任** | 评估的可信度 | confidence_score |

**评分标准范例**：
```
满分 (95-100): 
- 完整覆盖所有要点
- 逻辑清晰，论证充分
- 无事实错误
- 表述准确流畅

良好 (85-94):
- 涵盖大部分要点
- 逻辑基本清晰
- 没有重大错误
- 表述基本准确

中等 (70-84):
- 涵盖核心要点
- 逻辑有所不足
- 有轻微错误
- 表述欠缺准确

及格 (60-69):
- 涵盖部分要点
- 逻辑不够清晰
- 有显著错误
- 表述不够准确

不及格 (< 60):
- 缺少关键要点
- 逻辑混乱
- 多个错误
- 表述不准确
```

### 3. 概念提取 Prompt

**Prompt 模板**：
```
请从以下学习资料中提取核心概念和知识点：

资料内容：
{content}

要求：
1. 列出3-10个最重要的概念
2. 每个概念用简短的定义说明
3. 标记概念之间的关系

返回JSON格式：
{
    "concepts": [
        {
            "name": "概念名称",
            "definition": "简短定义",
            "importance": "high/medium/low",
            "related_concepts": ["相关概念1", "相关概念2"]
        }
    ]
}
```

### 4. 个性化学习计划 Prompt

**Prompt 模板**：
```
基于以下学生的学习表现，生成2周个性化学习计划：

学生弱点：
{weaknesses}

历史表现：
{performance_history}

学习资源：
{available_resources}

要求：
1. 专注于前3个弱点领域
2. 提供具体的学习路径
3. 推荐合适的学习资源
4. 设定可达成的目标

返回JSON格式：
{
    "plan": {
        "duration": "2周",
        "priority_areas": ["领域1", "领域2", "领域3"],
        "daily_goals": ["目标1", "目标2"],
        "resources": ["资源1", "资源2"],
        "checkpoints": ["检查点1", "检查点2"],
        "success_metrics": ["指标1", "指标2"]
    }
}
```

---

## Agent 设计过程

### Phase 1: 问题理解

```
用户输入 → 意图识别 → 任务分解
    ↓
确定任务类型：
• 学习材料处理
• 题目生成
• 答案评估
• 弱点分析
```

### Phase 2: 信息收集

```
信息收集
    ↓
┌──────────┬──────────┬──────────┐
▼          ▼          ▼          ▼
学习资料  用户历史   系统配置   外部知识
```

### Phase 3: 策略规划

```
        ┌─────────────────┐
        │  任务规划       │
        └────────┬────────┘
                 ▼
    ┌────────────────────────┐
    │ 选择合适的 Agent        │
    └────────────┬───────────┘
        ┌───────┴────────┬─────────────┐
        ▼                ▼             ▼
    DataProcessor  QuestionGenerator  AnswerEvaluator
```

### Phase 4: 执行与反馈

```
执行 → 验证 → 反馈 → 调整
  ↓      ↓      ↓      ↓
  └──────┴──────┴──────┘
         循环优化
```

### 设计模式

#### 模式 1: 链式调用（Chain of Agents）

```
DataProcessor
    ↓
    输出: Chunk 集合
    ↓
QuestionGenerator
    ↓
    输出: Question 列表
    ↓
用户作答
    ↓
AnswerEvaluator
    ↓
    输出: EvaluationResult
    ↓
MongoDBClient
    ↓
    保存记录
    ↓
WeaknessAnalyzer
    ↓
    输出: 学习分析
```

#### 模式 2: 并行处理

```
                   ┌─────────────────┐
                   │  QuestionGen    │
                   │  (批量生成)     │
                   └────────┬────────┘
                            ▼
                    [Q1, Q2, Q3, Q4, Q5]
                     │   │   │   │   │
                     ▼   ▼   ▼   ▼   ▼
                   [E1][E2][E3][E4][E5]  (并行评估)
                     │   │   │   │   │
                     └─────┬─────────┘
                           ▼
                   [R1, R2, R3, R4, R5]
```

#### 模式 3: 条件分支

```
                    题型判断
                      ↓
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
     选择题        简答题         真假题
    直接比对     LLM评估        规范化比对
        ▼             ▼             ▼
   EvaluationResult
```

---

## 工具链

### Tool 1: 数据处理工具

**功能**：
- PDF 文本提取
- 智能文本分块
- 关键概念提取

**调用接口**：
```python
from models.data_processor import DataProcessor

# 创建处理器
processor = DataProcessor(config)

# 处理 PDF
chunks = processor.process_input("file.pdf", input_type="pdf")

# 处理文本
chunks = processor.process_input("text content", input_type="text")

# 提取概念
concepts = processor.extract_key_concepts(chunks)
```

**内部工具**：
```
PyPDF           → 提取PDF文本
Tiktoken        → 精确计算Token
正则表达式      → 智能分块
OpenAI API      → 概念提取
```

### Tool 2: 题目生成工具

**功能**：
- 生成选择题、简答题、真假题
- 流式生成支持
- 难度自动分配

**调用接口**：
```python
from models.question_generator import QuestionGenerator

# 创建生成器
generator = QuestionGenerator(config)

# 生成题目
questions = generator.generate_questions(
    chunks=chunks,
    num_questions=5,
    question_types=["multiple_choice", "short_answer"],
    difficulty_mix="adaptive"
)

# 流式生成
questions = generator.generate_questions_stream(
    chunks=chunks,
    num_questions=5,
    on_question_start=lambda i, total: print(f"开始第 {i}/{total} 题"),
    on_question_chunk=lambda chunk: print(chunk, end=''),
    on_question_complete=lambda q: print(f"完成: {q.question_id}")
)
```

**难度分配算法**：
```python
def _select_difficulty(self, index: int, total: int) -> str:
    """
    自适应难度分配
    前期：easy → medium
    后期：medium → hard
    比例：30% easy, 40% medium, 30% hard
    """
    if index < total * 0.3:
        return "easy"
    elif index < total * 0.7:
        return "medium"
    else:
        return "hard"
```

### Tool 3: 答案评估工具

**功能**：
- 多题型评估
- Prometheus 框架评分
- 详细反馈生成

**调用接口**：
```python
from models.answer_evaluator import AnswerEvaluator

# 创建评估器
evaluator = AnswerEvaluator(config)

# 评估答案
result = evaluator.evaluate_answer(
    question=question,
    user_answer="用户答案",
    user_history=None
)

# 获取评估结果
print(f"得分: {result.score}")
print(f"反馈: {result.feedback}")
print(f"改进: {result.suggested_improvement}")
```

**评估流程**：
```
选择题/真假题         简答题
      ↓                 ↓
   直接比对      →  构建Prometheus Prompt
      ↓                 ↓
   二元判断      →  LLM评估推理
      ↓                 ↓
结果验证             结果验证
      ↓                 ↓
   返回结果            返回结果
```

### Tool 4: 弱点分析工具

**功能**：
- 用户表现分析
- 弱点识别
- 学习计划生成

**调用接口**：
```python
from models.weakness_analyzer import WeaknessAnalyzer

# 创建分析器
analyzer = WeaknessAnalyzer(mongo_client)

# 分析弱点
analysis = analyzer.analyze_user_weaknesses(
    user_id="user_123",
    time_range_days=30
)

# 生成学习计划
plan = analyzer.create_study_plan(analysis["weaknesses"])

# 生成针对性题目
targeted_qs = analyzer.generate_targeted_questions(
    weaknesses=analysis["weaknesses"],
    question_bank=all_questions
)
```

**弱点识别标准**：
```python
def identify_weakness(accuracy: float) -> bool:
    """准确率 < 70% 视为弱点"""
    return accuracy < 0.7
```

### Tool 5: 数据持久化工具

**功能**：
- MongoDB 数据存储
- 索引优化
- 数据查询

**数据集合**：

| 集合 | 用途 |
|------|------|
| `user_performance` | 用户答题记录 |
| `wrong_questions` | 错题本 |
| `learning_progress` | 学习进度 |

---

## 决策流程

### 1. 题目生成决策树

```
                生成题目请求
                    ↓
        ┌───────────────────────────┐
        │ 分析学习资料特征          │
        └───────────────────────────┘
                    ↓
        ┌───────────┬───────────┐
        ▼           ▼           ▼
    数据量?     复杂度?      关键概念?
    ↓           ↓           ↓
  小(<5K)    低         少(<5个)
  中(5-50K)  中         中(5-15个)
  大(>50K)   高         多(>15个)
                ↓
        ┌──────────────────────┐
        │ 确定题型分布          │
        └──────────────────────┘
                ↓
        ┌─────────┬─────────┬─────────┐
        ▼         ▼         ▼         ▼
      选择题    简答题    真假题    混合
      30%      40%      30%      根据难度
                ↓
        ┌──────────────────────┐
        │ 生成题目             │
        └──────────────────────┘
```

### 2. 难度调整决策

```
        用户答题表现
            ↓
        计算准确率
            ↓
    ┌───────┬────────┬───────┐
    ▼       ▼        ▼       ▼
 <60%    60-75%   75-90%   >90%
    ↓       ↓        ↓       ↓
  降低    保持     提升    大幅提升
  难度    难度     难度     难度
```

### 3. 评估方案选择

```
            题型判断
                ↓
    ┌───────────┼───────────┐
    ▼           ▼           ▼
 选择题     真假题       简答题
    ↓           ↓           ↓
直接比对    规范化比对    LLM评估
(精确)     (容错)       (语义)
    ↓           ↓           ↓
返回结果    返回结果      Prometheus评分
                            ↓
                        CoT推理
                        多维评估
                        返回结果
```

---

## 优化策略

### 1. 提示词优化

#### 策略 1.1: 链式思维（Chain of Thought）

**应用场景**：答案评估

**实现**：
```python
prompt = """
请按照以下步骤进行（CoT推理）：
1. 分析用户答案是否涵盖了参考答案的关键要点
2. 检查是否有事实性错误
3. 评估答案的完整性和准确性
4. 给出具体的改进建议
"""
```

**效果**：提高复杂推理的准确性 (↑15-25%)

#### 策略 1.2: Few-Shot 示例

**应用场景**：题目生成、概念提取

**实现**：
```python
prompt = f"""
生成题目示例：
示例1: {example_question_1}
示例2: {example_question_2}

现在，请基于以下资料生成类似格式的题目：
{content}
"""
```

**效果**：提高输出质量和格式一致性 (↑10-20%)

#### 策略 1.3: 角色提示

**应用场景**：答案评估

**实现**：
```python
prompt = """
你是一个公平、客观的评估专家。
• 避免过于严格或宽松
• 考虑答案的多样性
• 认可部分正确的答案
"""
```

**效果**：提高评估公平性和多维度考虑 (↑20-30%)

### 2. 参数优化

#### 温度参数

| 任务 | 温度 | 理由 |
|------|------|------|
| 题目生成 | 0.7 | 保持创意，避免过度随机 |
| 答案评估 | 0.1 | 保持一致性，减少随机性 |
| 概念提取 | 0.3 | 平衡稳定性和多样性 |

#### 输出限制

```python
# Token 限制
max_tokens_question = 1024     # 题目生成
max_tokens_evaluation = 2048   # 答案评估
max_tokens_concept = 512       # 概念提取
```

### 3. 缓存策略

#### 缓存层级

```
         请求
            ↓
     ┌──────┴──────┐
     ▼             ▼
  本地缓存    Redis缓存
  (内存)      (持久化)
     ↓             ↓
  HIT    → 返回  HIT    →返回
     ↓             ↓
  MISS    →继续   MISS   →API调用
                         ↓
                      更新Redis
                      更新本地
                      返回结果
```

#### 缓存对象

```python
# 题目缓存
self.question_cache = {
    "q_id_1": Question(),
    "q_id_2": Question(),
}

# 概念缓存
self.concept_cache = {
    "content_hash": [Concept()]
}
```

### 4. 流式处理优化

**实现流式生成**：
```python
def generate_questions_stream(
    self,
    chunks,
    on_question_start,
    on_question_chunk,
    on_question_complete
):
    for i in range(num_questions):
        # 通知开始
        on_question_start(i + 1, num_questions)
        
        # 流式获取
        for chunk in self._stream_question_generation():
            on_question_chunk(chunk)  # 实时回调
        
        # 通知完成
        on_question_complete(question)
```

**用户体验提升**：
- ✅ 实时反馈
- ✅ 减少等待感
- ✅ 支持中断

### 5. 错误处理与降级

#### 降级方案

```python
# 评估失败时的备用方案
def _fallback_evaluation(self, question, user_answer):
    return EvaluationResult(
        is_correct=False,
        score=50,           # 中等分数
        feedback="自动评估系统暂时不可用",
        # ...
        confidence_score=0.5  # 低置信度标记
    )
```

#### 重试机制

```python
RETRY_LIMIT = 3
for attempt in range(RETRY_LIMIT):
    try:
        result = self.evaluate_answer(question, answer)
        return result
    except APIError as e:
        if attempt < RETRY_LIMIT - 1:
            time.sleep(2 ** attempt)  # 指数退避
        else:
            return fallback_evaluation()
```

### 6. 质量评估

#### 指标

| 指标 | 说明 | 目标 |
|------|------|------|
| **准确率** | 评估结果准确性 | > 90% |
| **一致性** | 相同问题评分一致 | > 95% |
| **覆盖率** | 包含主要知识点 | > 85% |
| **响应时间** | API 调用时间 | < 30s |
| **置信度** | 评估的可信度 | > 0.8 |

#### 测试数据集

```python
# 验证集
test_questions = [
    {
        "question": "...",
        "answer": "...",
        "expected_score": 85,
        "tolerance": ±5
    }
]

# A/B 测试
prompt_v1_results = []
prompt_v2_results = []
compare_metrics(prompt_v1_results, prompt_v2_results)
```

---

## 高级特性

### 1. 适应学习 (Adaptive Learning)

**原理**：根据用户表现动态调整题目难度

```python
def adaptive_difficulty_adjustment(user_performance):
    if accuracy > 0.9:
        return "hard"      # 95%+ 正确率 → 难题
    elif accuracy > 0.7:
        return "medium"    # 70-95% → 中等难度
    else:
        return "easy"      # <70% → 简单题巩固
```

### 2. 个性化推荐

**基于弱点的推荐**：
```python
weaknesses = analyzer.identify_weaknesses(user_id)
recommended_topics = generate_recommendations(weaknesses)
recommended_questions = get_targeted_questions(recommended_topics)
```

### 3. 学习路径规划

**自适应路径**：
```
初始诊断 → 弱点识别 → 路径规划 → 逐步推进 → 定期复习
  ↓                                            ↓
 Easy                                      Challenging
```

---

## 总结

**LLMAgent 的核心竞争力**：

| 特性 | 优势 |
|------|------|
| **多模块设计** | 清晰的职责分工，易于维护和扩展 |
| **Prometheus 评分** | 公平、透明的评估过程 |
| **适应学习** | 个性化体验，提高学习效率 |
| **流式输出** | 实时反馈，改善用户体验 |
| **多题型支持** | 全面评估，提高准确性 |
| **数据驱动** | 基于历史表现优化建议 |

**未来发展方向**：
- 🚀 多语言支持
- 🚀 视频内容处理
- 🚀 社交学习功能
- 🚀 更细粒度的知识图谱
- 🚀 实时协作编辑
