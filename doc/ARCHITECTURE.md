# 系统架构设计文档

## 目录
1. [系统概述](#系统概述)
2. [架构设计](#架构设计)
3. [核心组件](#核心组件)
4. [技术栈](#技术栈)
5. [数据流](#数据流)
6. [部署架构](#部署架构)

---

## 系统概述

**LLMAgent 学习评估与巩固系统**是一个基于大型语言模型（LLM）的个性化学习智能体系统，能够自动生成评估题目、智能判卷、分析学习弱点，并提供个性化学习建议。

### 系统目标
- 🎯 自动化题目生成：从学习资料中自动提取知识点生成评估题目
- 📊 智能评估：使用LLM进行多维度的答案评估
- 🔍 弱点分析：识别学生知识薄弱环节
- 💡 个性化指导：根据用户表现生成学习计划

### 核心特性
- 支持多种题目类型（选择题、简答题、真假题）
- 支持多种输入格式（文本、PDF）
- 流式输出支持，实时反馈
- 完整的错题本管理
- 学习进度追踪

---

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户交互层 (CLI)                            │
│                 InteractiveCLI - 富交互界面                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    LLMAgent 核心引擎层                           │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────┐             │
│  │  问题生成器   │  │  答案评估器 │  │  弱点分析器  │             │
│  │ Question     │  │ Answer     │  │ Weakness   │             │
│  │ Generator    │  │ Evaluator  │  │ Analyzer   │             │
│  └──────────────┘  └────────────┘  └─────────────┘             │
│          │                │                │                    │
│          └────────────────┼────────────────┘                    │
│                           │                                      │
│                   ┌───────▼────────┐                             │
│                   │ 数据处理器      │                             │
│                   │DataProcessor   │                             │
│                   └───────┬────────┘                             │
└─────────────────────┬─────┴────────────────────────────────────┘
                      │                      │
        ┌─────────────▼──────┐   ┌──────────▼────────────┐
        │  OpenAI LLM API    │   │  MongoDB 数据库       │
        │  (DeepSeek-V3.2)   │   │  (持久化存储)         │
        │  (Qwen3-Embedding) │   │  - 用户表现           │
        │                    │   │  - 错题本             │
        │                    │   │  - 学习进度           │
        └────────────────────┘   └───────────────────────┘
```

### 分层架构

```
┌──────────────────────────────────────┐
│      表现层 (Presentation Layer)      │
│   CLI 界面、富文本输出、交互体验      │
└──────────────────────────────────────┘
                  ▲
                  │
┌──────────────────────────────────────┐
│      业务逻辑层 (Business Logic)      │
│  • LLMAgent 核心引擎                 │
│  • 题目生成算法                       │
│  • 答案评估逻辑                       │
│  • 弱点分析引擎                       │
└──────────────────────────────────────┘
                  ▲
                  │
┌──────────────────────────────────────┐
│       数据处理层 (Data Layer)         │
│  • 文件解析 (PDF、文本)               │
│  • 文本分块                           │
│  • 向量化处理                         │
└──────────────────────────────────────┘
                  ▲
                  │
┌──────────────────────────────────────┐
│      外部服务层 (External Services)   │
│  • OpenAI API 调用                    │
│  • MongoDB 数据持久化                 │
└──────────────────────────────────────┘
```

---

## 核心组件

### 1. LLMAgent（主控引擎）

**职责**：协调各子模块，管理用户会话和数据流

```python
class LLMAgent:
    """学习评估和巩固智能体"""
    
    def __init__(self, config):
        self.data_processor = DataProcessor()      # 数据处理
        self.question_generator = QuestionGenerator()  # 题目生成
        self.answer_evaluator = AnswerEvaluator()     # 答案评估
        self.weakness_analyzer = WeaknessAnalyzer()    # 弱点分析
        self.mongo_client = MongoDBClient()            # 数据持久化
```

**关键方法**：
- `process_material()`: 处理学习资料（支持 PDF/文本）
- `generate_questions()`: 生成评估题目
- `generate_questions_stream()`: 流式生成题目（实时反馈）
- `evaluate_answer()`: 评估用户答案
- `analyze_weaknesses()`: 分析学生弱点

### 2. DataProcessor（数据处理器）

**职责**：处理多种格式的学习资料，进行智能分块和向量化

**功能**：
- **PDF处理**：提取文本、逐页处理
- **智能分块**：
  - 按语义单位分割
  - 保持上下文完整性
  - Token限制（≤1000 tokens/块）
- **概念提取**：识别核心知识点

**流程**：
```
输入资料 → 格式识别 → 文本提取 → 智能分块 → 概念提取 → Chunk集合
```

### 3. QuestionGenerator（题目生成器）

**职责**：基于学习资料和关键概念生成多种题型的评估题目

**支持的题型**：
1. **选择题 (Multiple Choice)**
   - 4个选项
   - 基于学习内容编造干扰项
   
2. **简答题 (Short Answer)**
   - 开放式回答
   - 需要LLM语义理解
   
3. **真假题 (True/False)**
   - 二选一
   - 快速评估掌握度

**难度调控**：
- 简单 (Easy): 基础概念
- 中等 (Medium): 应用理解
- 困难 (Hard): 深度分析综合

**生成策略**：
```
学习资料块 → 关键概念提取 → 难度分配
    ↓
选择题生成: LLM → 主题 + 4个选项
简答题生成: LLM → 问题 + 预期答案
真假题生成: LLM → 陈述 + 正确答案

↓
输出: Question对象列表
```

**流式生成**：
```
支持实时回调：
- on_question_start(): 题目开始生成
- on_question_chunk(): 流式内容块
- on_question_complete(): 题目生成完成
```

### 4. AnswerEvaluator（答案评估器）

**职责**：对用户答案进行多维度评估，使用 Prometheus 评分模式

**评估维度**：

| 题型 | 评估逻辑 | 评分方式 |
|------|---------|---------|
| 选择题 | 直接比对 | 二元 (0/100) |
| 真假题 | 规范化比对 | 二元 (0/100) |
| 简答题 | LLM 语义评估 | 分数 (0-100) + 详解 |

**答案规范化**：
```python
# 真假题答案支持多种格式
true_variations = ["true", "t", "是", "对", "yes", "y"]
false_variations = ["false", "f", "否", "错", "no", "n"]
```

**输出结构** (EvaluationResult)：
- `is_correct`: 是否正确
- `score`: 得分 (0-100)
- `feedback`: 反馈信息
- `detailed_explanation`: 详细解析
- `suggested_improvement`: 改进建议
- `confidence_score`: 评估置信度
- `mistakes`: 错误点分析

### 5. WeaknessAnalyzer（弱点分析器）

**职责**：分析用户学习表现，生成个性化学习计划

**分析流程**：
```
用户历史表现 → 按标签分类 → 计算准确率
    ↓
识别弱点 (准确率 < 70%)
    ↓
生成改进建议 + 学习计划
    ↓
推荐针对性题目
```

**核心功能**：
- **弱点识别**：准确率低于70%的知识点
- **错题本管理**：记录所有错误题目
- **趋势分析**：追踪学习进度
- **学习计划**：
  - 2周提升计划
  - 优先学习领域
  - 每日学习目标
  - 推荐资源

### 6. MongoDBClient（数据持久化层）

**职责**：管理所有数据的持久化存储

**数据集合**：

| 集合名 | 用途 | 关键字段 |
|--------|------|---------|
| `user_performance` | 用户答题记录 | user_id, question_id, is_correct, score, tags |
| `wrong_questions` | 错题本 | user_id, question_id, review_count, created_at |
| `learning_progress` | 学习进度 | user_id, subject, accuracy, completion_rate |

**索引优化**：
```python
# 用户表现查询优化
db.user_performance.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
db.user_performance.create_index([("user_id", ASCENDING), ("tags", ASCENDING)])

# 错题本查询优化
db.wrong_questions.create_index([("user_id", ASCENDING), ("question_id", ASCENDING)], unique=True)
```

---

## 技术栈

### 后端框架
| 组件 | 技术 | 用途 |
|------|------|------|
| **LLM 引擎** | OpenAI API (DeepSeek-V3.2) | 题目生成、答案评估 |
| **向量化** | Qwen3-Embedding-8B | 文本向量化 |
| **数据库** | MongoDB 7.0 | 数据持久化 |
| **文档解析** | PyPDF | PDF 文本提取 |
| **Token计算** | Tiktoken | 精确的 Token 统计 |

### 依赖包
```txt
openai                  # OpenAI API 客户端
pymongo                 # MongoDB 客户端
pypdf                   # PDF 处理
python-dotenv           # 环境变量管理
tiktoken                # Token 编码/解码
rich                    # 富文本输出
questionary             # 交互式问卷
numpy                   # 数值计算
pydantic                # 数据验证
```

### 容器化与编排
- **Docker**: 应用容器化
- **Docker Compose**: 本地开发编排
- 支持 Kubernetes (K8s) 部署

---

## 数据流

### 典型工作流

```
用户输入资料
    ↓
┌─────────────────────────────┐
│   DataProcessor 处理        │
│ • PDF/文本解析              │
│ • 智能分块                  │
│ • 概念提取                  │
└─────────────┬───────────────┘
              ↓
         Chunk 集合
              ↓
┌─────────────────────────────┐
│  QuestionGenerator 生成      │
│ • 选择题、简答题、真假题    │
│ • 难度分配                  │
│ • 流式输出                  │
└─────────────┬───────────────┘
              ↓
         Question 对象
              ↓
用户作答
              ↓
┌─────────────────────────────┐
│  AnswerEvaluator 评估        │
│ • 答案比对/理解             │
│ • 评分                      │
│ • 反馈生成                  │
└─────────────┬───────────────┘
              ↓
      EvaluationResult
              ↓
┌─────────────────────────────┐
│  MongoDBClient 保存          │
│ • 用户表现                  │
│ • 错题记录                  │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│  WeaknessAnalyzer 分析       │
│ • 弱点识别                  │
│ • 趋势分析                  │
│ • 学习计划                  │
└─────────────────────────────┘
```

### 数据模型

#### Chunk（数据块）
```python
@dataclass
class Chunk:
    text: str                          # 文本内容
    metadata: Dict[str, Any]           # 元数据（来源、页码等）
    embedding: Optional[List[float]]   # 向量表示
```

#### Question（问题）
```python
@dataclass
class Question:
    question_id: str           # 唯一标识
    question_type: str         # 题型（multiple_choice/short_answer/true_false）
    content: str               # 问题内容
    options: List[str]         # 选项（如适用）
    correct_answer: str        # 标准答案
    explanation: str           # 解析
    difficulty: str            # 难度（easy/medium/hard）
    source_chunks: List[str]   # 来源数据块
    tags: List[str]            # 标签（知识点）
    metadata: Dict[str, Any]   # 元数据
```

#### EvaluationResult（评估结果）
```python
@dataclass
class EvaluationResult:
    is_correct: bool           # 是否正确
    score: float               # 得分 (0-100)
    feedback: str              # 反馈信息
    detailed_explanation: str  # 详细解析
    suggested_improvement: str # 改进建议
    confidence_score: float    # 置信度
    mistakes: List[str]        # 错误点
```

---

## 部署架构

### Docker Compose 本地开发

```yaml
services:
  mongodb:
    image: mongo:7.0
    ports: ["27017:27017"]
    healthcheck: 10s interval
    
  app:
    build: ./Dockerfile
    depends_on:
      - mongodb (service_healthy)
    environment:
      - MONGO_URI: mongodb://root:password123@mongodb:27017/learning_agent
      - OPENAI_API_KEY: ${OPENAI_API_KEY}
      - ENABLE_STREAM: True
      - DEBUG: False
```

### 容器化配置

**Dockerfile 特点**：
- 基础镜像: `python:3.12-slim`
- 多阶段优化（可选）
- 非 root 用户运行 (appuser)
- 环境变量配置
- 健康检查

### 云原生支持

#### 1. Kubernetes 部署（推荐）
```yaml
# 支持的资源
- Deployment: 应用副本管理
- Service: 网络暴露
- ConfigMap: 配置管理
- Secret: 敏感信息管理
- PersistentVolume: MongoDB 数据持久化
```

#### 2. Serverless 支持
- AWS Lambda + API Gateway
- Azure Functions
- 支持无状态请求处理
- 自动扩容

#### 3. 微服务拆分（可选）

```
┌──────────────────────────────────────┐
│        API Gateway                   │
└──────────────┬───────────────────────┘
         ┌─────┴─────────────────────┐
         ▼                           ▼
    ┌─────────────┐        ┌──────────────┐
    │ Question    │        │ Answer       │
    │ Generator   │        │ Evaluator    │
    │ Service     │        │ Service      │
    └─────────────┘        └──────────────┘
         ▲                           ▲
         └─────────────┬─────────────┘
                       ▼
              ┌──────────────────┐
              │  Data Service    │
              │  (MongoDB)       │
              └──────────────────┘
```

#### 4. 存储方案
- **MongoDB Atlas**: 云托管数据库
- **Redis**: 缓存层（可选）
  - 缓存生成的题目
  - Session 管理
  - 速率限制

---

## 环境配置

### 必需环境变量

```bash
# OpenAI 配置
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1/
OPENAI_MODEL=deepseek-ai/DeepSeek-V3.2
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B

# MongoDB 配置
MONGO_URI=mongodb://root:password123@mongodb:27017/learning_agent
MONGO_DB=learning_agent

# 功能配置
ENABLE_STREAM=True
DEBUG=False
```

---

## 性能指标

### 系统容量
- **同时用户**: 100+ (取决于硬件)
- **并发请求**: 支持异步处理
- **数据库连接池**: 配置可调

### 响应时间
- **文本处理**: < 1 秒
- **PDF 处理**: < 5 秒 (取决于大小)
- **题目生成**: 10-30 秒 (取决于题量)
- **答案评估**: 5-15 秒

### 成本优化
- 使用 embedding 缓存减少 API 调用
- 批量处理题目
- MongoDB 索引优化

---

## 安全考虑

1. **API 密钥管理**
   - 使用环境变量
   - 支持 .env 文件
   - 不在代码中硬编码

2. **数据库安全**
   - MongoDB 认证启用
   - 网络隔离
   - 定期备份

3. **输入验证**
   - 文件大小限制
   - 字符编码检查
   - SQL 注入防护 (PyMongo 内置)

---

## 扩展点

### 可扩展功能
1. **多语言支持**: 支持多种语言的题目生成
2. **视频内容处理**: 支持视频转录和处理
3. **实时协作**: 支持多用户协作学习
4. **移动端**: REST API + 移动应用
5. **插件系统**: 自定义评估模型

---

## 总结

本系统采用**分层架构**设计，通过明确的职责分离实现高内聚、低耦合。核心使用 **LLM + 数据库** 的组合，支持**本地、容器化、云原生**多种部署方式，是一个**可扩展、易维护**的学习评估系统。
