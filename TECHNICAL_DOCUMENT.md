# 项目技术文档

## 1. 架构设计

### 1.1 系统架构设计

本项目采用基于微服务理念的云原生架构，以容器化方式部署，围绕 LLM Agent 协同工作的模式构建跨学科知识图谱生成系统。系统整体分为 **前端交互层**、**后端智能体服务层** 和 **基础设施层**。

**核心架构组件：**

*   **前端 (Frontend)**: 基于 Vue 3 + Vite 构建的 SPA 单页应用，提供聊天界面、使用 Force Graph 构建图谱可视化交互、构建流程监控等功能。
*   **后端服务 (Backend Services)**:
    *   **Central Agent (FastAPI)**: 系统的核心中枢，负责统一 API 暴露、任务状态管理、以及协调 Search Agent 和 Knowledge Engine 的工作流。
    *   **Search Agent**: 负责跨学科知识检索。基于 LangGraph 构建的状态机，实现从概念分类、并行搜索到结果验证的全流程自动化。
    *   **Knowledge Engine**: 负责知识处理与存储。集成 **LightRAG** 框架进行图谱构建（实体/关系提取），并同步数据至 Neo4j 图数据库。
*   **基础设施 (Infrastructure)**:
    *   **Neo4j**: 高性能图数据库，存储构建好的学科知识图谱，支持 Cypher 查询。
    *   **Vector Embeddings**: 本地挂载的 embedding 模型（初始化时会自动联网下载，减少分发包体积），用于 LightRAG 的文本向量化。

### 1.2 云原生组件与技术栈

系统合理地采用了云原生技术架构，以确保部署的灵活性和环境的一致性：

*   **Docker & Docker Compose**: 全系统容器化封装。`backend` 和 `frontend` 均编写了 `Dockerfile`，并通过 `docker-compose.yml` 进行统一编排和服务发现。这种方式使得应用可以在任何支持 Docker 的 Linux 环境中“一次构建，到处运行”，极大地简化了运维复杂度。
*   **Microservices (Lite) Architecture**: 后端采用模块化设计，Search Agent、Knowledge Engine 和 API 服务逻辑解耦。虽然目前为了简化演示部署在单容器中，但各个组件具备拆分为独立微服务的原生能力（Microservices Ready）。
*   **Neo4j (Containerized)**: 使用官方 Docker 镜像部署图数据存储服务，配置了持久化卷 (`volumes`) 保证数据安全，利用容器网络实现服务间的高速通信。
*   **Embedding Model Volume**: 通过 Docker Volume 将宿主机预下载的模型挂载至容器内部，避免镜像过大（Slim Image），同时加速容器启动时间。
*   **FastAPI**: 选择 FastAPI 不仅因为其高性能，更因为它对异步（Async）的原生支持，完美适配 LLM Agent 这种高并发 IO 密集型（等待模型响应）的场景。

### 1.3 LLM Agent 工具链

*   **LangGraph**: 用于构建 Search Agent 的状态机（StateGraph），管理 Agent 的执行流程（Search -> Validate -> Construct -> Ingest）和状态流转。
*   **DeepSeek / OpenAI API**: 核心大语言模型，用于概念分类、结果验证、实体抽取和关系推理。
*   **Tavily API**: 专为 LLM 设计的搜索引擎接口，提供高质量的 web 搜索结果。
*   **Pydantic**: 强类型数据校验，定义了系统内部流转的标准数据模型（如 `Chunk`, `SearchItem`），保证 Agent 间交互的稳定性。
*   **LightRAG**: 并不是简单的 RAG，而是基于图的 RAG 框架，负责将非结构化文档转化为结构化的图谱数据。

### 1.4 系统稳定性与可扩展性设计

*   **稳定性保障 (Stability)**:
    *   **强类型约束**: 全面使用 Python 的 `Pydantic` 进行数据模型定义和校验，确保 Agent 间传递的数据结构（如 JSON Schema）严格符合预期，减少运行时错误。
    *   **环境隔离**: 基于 Docker 容器化部署，确保开发、测试与生产环境的一致性，避免依赖冲突。
    *   **异常处理**: 核心服务（如 Search Agent）实现了完善的错误捕获与重试机制，防止因单个请求失败导致整个任务流崩溃。

*   **可扩展性 (Scalability)**:
    *   **微服务就绪 (Microservices Ready)**: 系统模块（Central UI, Search, Knowledge）虽然目前共存在单体中，但已通过 API 接口进行逻辑解耦。未来可轻松拆分为独立的微服务容器，配合 K8s 进行弹性伸缩。
    *   **异步并发**: 采用 `FastAPI` + `asyncio` 的全异步架构，能够高效处理大量并发的 LLM 请求和网络 IO，支持高负载下的稳定运行。
    *   **模块化组件**: 新增搜索源（如 Arxiv）或更换 LLM 模型（如切换至 GPT-4）仅需扩展相应的 Base 类或配置，无需重构核心逻辑。

---

## 2. 项目分工

以下是项目每位成员的具体负责模块：

*   **陈子谦**：**前端开发**
    *   负责 Vue3 框架搭建、UI 组件开发（ChatPanel, GraphView 等）
    *   实现与后端 API 的交互及可视化展示（力导向图展示知识结构）
    *   负责整体架构设计和前后端对接协调
*   **李则言**：**Agent 并行搜索**
    *   负责 Search Agent 的核心逻辑实现
    *   利用 `asyncio` 和 `LangGraph` 实现多学科关键词的并发搜索策略，提升检索效率和广度
    *   设计搜索结果的清洗与验证机制
*   **李佳亮**：**LightRAG 知识图谱构建**
    *   负责 Knowledge Engine 的研发
    *   集成 LightRAG 框架进行文档处理、实体识别和关系抽取
    *   实现图数据到 Neo4j 的同步与持久化存储

---

## 3. 智能体策略 (Agent Strategy)

项目的核心智能主要体现在 **Search Agent** 的自动化作业流程中。通过精密设计的 Prompt 和 LangGraph 编排，模拟人类专家的研究过程。

### 3.1 LLM Agent 设计过程

Search Agent 的工作流是一个有向无环图（DAG），包含以下关键节点：

1.  **分类与规划 (Classification & Planning)**:
    *   **输入**: 用户提供的核心概念。
    *   **策略**: 调用 LLM 扮演“跨学科专家”，将概念拆解为多个学科视角（如物理学、信息论、计算机科学），并生成对应的专业搜索关键词。
2.  **并行搜索 (Parallel Search Node)**:
    *   **输入**: 分类后的学科及其关键词。
    *   **策略**: 利用 Python 的 `asyncio.gather` 并发执行多个学科维度的搜索请求（Tavily为主, Wikipedia作为fallback）。这一步大大缩短了信息收集的时间，同时保证了信息来源的多样性。
3.  **结果验证 (Validation Node)**:
    *   **输入**: 原始搜索结果列表。
    *   **策略**: LLM 扮演“质量审核员”，阅读搜索摘要，根据**学术价值**和**相关性**对结果进行打分。过滤掉广告、低质量内容，确保后续图谱构建的源数据质量。
4.  **构建与入库 (Construct & Ingest Node)**:
    *   **输入**: 验证通过的高质量片段 (Chunks)。
    *   **策略**: 将片段标准化封装为 `Chunk` 对象，推送到 Knowledge Engine，触发 LightRAG 的图构建流水线。

### 3.2 关键 Prompt 模板展示

系统使用了高度结构化且严谨的 System Prompt 来引导 LLM 完成特定子任务。这些 Prompt 经过精心设计和多次迭代，包含了明确的角色设定（Persona）、具体的任务指令（Instruction）以及严格的输出格式约束（Output Constraint），以最大限度减少 LLM 的不确定性和模型幻觉。

**1. 学科分类 Prompt (Classify Prompt)**

该 Prompt 用于将用户输入的单一概念发散为跨学科的研究视角，是知识图谱广度的来源。

```python
CLASSIFY_PROMPT = """\
你是一个跨学科知识专家。给定一个核心概念，分析它在不同学科领域中的应用和关联。

核心概念: {concept}

请只返回 JSON（不要解释、不要 Markdown），格式如下：
{{
  "concept": "{concept}",
  "primary_discipline": "学科名",
  "disciplines": [
    {{
      "name": "学科名称",
      "relevance_score": 0.95,
      "reason": "关联理由（具体、有学术价值）",
      "search_keywords": ["关键词1","关键词2","关键词3"]
    }}
  ],
  "suggested_additions": [
    {{
      "name": "可选学科",
      "reason": "为什么可能相关"
    }}
  ]
}}

要求：
- disciplines 至少 3 个；尽量包含“远亲概念”学科
- relevance_score ∈ [0,1]，按相关性降序
"""
```

**2. 结果验证 Prompt (Validate Prompt)**

该 Prompt 用于清洗搜索带来的噪声，确保数据的“信噪比”。

```python
VALIDATE_PROMPT = """\
你是检索结果的质量审核员。根据核心概念判断每条结果是否值得用于后续知识图谱构建。

核心概念：{concept}

候选结果（JSON数组）：{items_json}

请只返回 JSON，格式：
{{
  "validated": [
    {{
      "url": "...",
      "relevance_score": 0.0,
      "academic_value": 0.0,
      "is_valid": true,
      "notes": "简短原因"
    }}
  ],
  "rejected": [
    {{
      "url": "...",
      "reason": "简短原因"
    }}
  ]
}}

规则：
- 明显广告/论坛灌水/与概念无关 => rejected
- validated 中给出 relevance_score 与 academic_value ∈ [0,1]
"""

```

### 3.3 鲁棒性与防幻觉设计 (Robustness & Anti-Hallucination)

针对 LLM 常见的幻觉和不稳定问题，系统采取了多重防御策略：

1.  **严格的 JSON 格式强制 (Strict JSON Enforcement)**:
    *   在 Prompt 中明确要求 `JSON` 格式输出，并配合 Pydantic 的校验器。如果 LLM 返回了无法解析的格式，系统会触发重试机制或降级处理，而不是让错误向下游传播。
2.  **基于证据的生成 (Evidence-Based Generation)**:
    *   Agent 绝不凭空生成知识。所有的图谱构建都严格基于 Search Agent 检索并验证过的 `Source Chunks`（真实来源片段）。
    *   在构建节点时，系统维护了从 **Graph Node -> Chunk -> Source URL** 的完整溯源链路，每一条知识都有据可查。
3.  **双重验证机制 (Dual Validation)**:
    *   引入独立的 **Validation Node**。生成内容不仅仅是“生成”，还必须通过“审核”。LLM 被要求扮演批判性的审核员角色，对检索内容的学术价值进行评分，低分内容直接丢弃。
4.  **异常输入防御 (Abnormal Input Handling)**:
    *   对于用户的恶意输入或非结构化查询，分类器（Classification Node）会首先尝试将其归一化为标准概念。如果输入无法识别，系统将返回友好的错误提示，而不是执行错误的搜索逻辑。

## 4. 前端流程技术设计 (Frontend Process Design)

前端应用采用 Vue 3 的 Composition API 风格构建，利用 Pinia 进行全局状态管理，实现了从用户输入到最终图谱呈现的完整闭环流程。

**交互流程实现：**
用户在首页输入核心概念后，前端触发 `/api/search/start` 接口启动异步任务。为了实时反馈复杂的后端处理进度，前端设计了轮询（Polling）机制，在 `BuildProcess.vue` 视图中通过 `searchStore` 定时拉取任务状态。系统将构建过程细化为 "概念分析"、"广泛检索"、"深度阅读" 和 "图谱生成" 四个可视化阶段，通过进度条和实时日志流（Log Stream）让用户感知后台智能体的思考过程，消除了等待焦虑。

**数据流转与渲染：**
当后端完成图谱构建后，前端接收标准的 JSON 图数据（Nodes & Edges）。图谱展示组件 `GraphView.vue` 集成了力导向图引擎，能够处理大规模节点的自动布局。点击节点时，右侧抽屉组件 `NodeDetail.vue` 会异步加载该节点关联的原始文档片段（Chunks），实现了从宏观知识结构到微观证据来源的无缝下钻（Drill-down）体验。

## 5. 检索 Agent 详解 (Search Agent Deep Dive)

检索 Agent 是系统获取外部知识的触手，其核心设计目标是“广度”与“精度”的平衡。

**多源异构检索架构：**
为了克服单一数据源的局限性，Agent 内部封装了 `SearchService` 类，支持多种搜索源的插件化接入。目前集成了 **Tavily Search API** 用于获取广阔的互联网实时信息，以及 **Wikipedia API** 用于获取结构化程度较高的百科知识。Agent 能够根据任务规划阶段确定的学科领域，自动选择最合适的检索策略。

**高并发与智能验证：**
在执行层，Agent 充分利用了 Python 的 `asyncio` 异步特性。系统并非串行地搜索每个关键词，而是生成一组并行协程（Coroutines），同时向多个数据源发起请求。收集到的原始数据会进入“验证管道”，由 LLM 扮演的审核员根据预设的 `VALIDATE_PROMPT` 进行学术价值打分。只有相关度（Relevance Score）和学术价值（Academic Value）均超过阈值的片段，才会被清洗并保留，确保了进入知识库的信息不仅“相关”，而且“可信”。

## 6. 图谱集成 LightRAG (Graph Integration with LightRAG)

知识引擎（Knowledge Engine）并不单纯依赖传统的向量检索，而是引入了先进的 **LightRAG** 框架，实现了“基于图的检索增强生成”。

**深度集成方案：**
系统通过 `RAGEngine` 类封装了 LightRAG 的复杂性。在数据层，我们采用了混合存储策略：本地文件系统存储 LightRAG 生成的中间状态（如 KV 存储、图结构缓存），同时将最终生成的实体与关系同步至 **Neo4j** 图数据库以供持久化查询。为了适应中文知识环境，系统内置了 `SentenceTransformer` 并挂载了 `BAAI/bge-large-zh-v1.5` 模型，在容器本地完成高性能的文本向量化（Embedding），避免了对外部 Embedding API 的依赖。

**动态工作区管理：**
为了支持多任务并发与数据隔离，系统为每个核心概念（Concept）维护独立的 LightRAG 工作区 (`/app/lightrag_workdir/{concept}`)。这意味着不同领域的知识构建互不干扰，Agent 可以针对特定概念通过 `ingest_and_build_graph` 方法动态加载对应的索引上下文。这种设计不仅提升了检索的精准度，也为后续支持多用户的个性化知识库奠定了基础。


