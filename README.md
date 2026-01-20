# AutoKGS: 跨学科知识图谱智能体

## 1. 项目背景与目标

**痛点场景**：
在现代教育与科研中，知识碎片化现象严重。学生难以洞察不同学科间（如神经科学与深度学习、热力学与信息论）的内在关联，导致知识体系割裂。

**核心目标**：
构建一个基于多智能体（Multi-Agent）协作的系统，自动挖掘跨领域概念的桥梁，并构建可视化的知识图谱，帮助用户发现“远亲概念”的逻辑联系。

**功能清单**：
- **深度关联挖掘**：利用智能体在不同学科领域（数学、物理、社会学等）自动寻找相关概念。
- **自动化图谱构建**：从非结构化文本中提取实体及其关系，生成标准化的图结构数据。
- **交互式可视化**：提供 Web 端动态交互界面，支持力导向图的拖拽、缩放与点击跳转。
- **幻觉校验机制**：引入审计智能体（Auditor Agent）对生成内容进行学术引用校验，确保准确性。

---

## 2. 系统架构 (System Architecture)

本系统采用 **微服务架构** 与 **云原生 (Cloud-Native)** 部署方案，实现了计算、存储与表现层的完全解耦。

### 2.1 核心流程

```mermaid
graph TD
    %% --- 样式定义 (保持不变) ---
    classDef eng fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef ai fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef db fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef ext fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,stroke-dasharray: 5 5
    classDef err fill:none,stroke:#c62828,stroke-width:2px,stroke-dasharray: 5 5,color:#c62828

    %% --- 外部交互 ---
    User(("用户 User")) -->|"1.输入关键词"| FE
    FE -->|"10.渲染图谱展示"| User

    %% --- Member A: 架构与工程 (Infrastructure) ---
    subgraph GroupA ["Member A: 架构与工程 (Infrastructure)"]
        direction TB
        FE["前端容器 Frontend"]:::eng
        API["后端容器 Backend API"]:::eng
        Redis[("消息队列 Redis")]:::db
        Neo4j[("图数据库 Neo4j")]:::db
        VectorDB[("向量数据库 VectorDB<br/>(Chroma 存教科书)")]:::db
        
        FE <-->|"2.HTTP请求/轮询"| API
        API -->|"3.发布任务 (PUSH)"| Redis
        
        API <-->|"8.读取图谱数据 (Query)"| Neo4j
        API -->|"9.返回完整数据"| FE
    end

    %% --- 外部学术资源 ---
    Arxiv(("外部学术资源<br/>(ArXiv API 查论文)")):::ext

    %% --- Member B: 智能体策略 (Agent Strategy) ---
    subgraph GroupB ["Member B: 智能体策略 (Agent Pipeline)"]
        direction TB
        Worker["Worker 容器 (Agent Runner)"]:::eng
        
        subgraph Pipeline ["Agent Pipeline (LangGraph)"]
            Planner("Planner Agent<br/>(路径规划)"):::ai
            Miner("Miner Agent<br/>(混合检索)"):::ai
            Builder("Graph Builder<br/>(JSON构建)"):::ai
            Auditor("Auditor Agent<br/>(幻觉校验)"):::ai
        end
        
        Redis -->|"4.领取任务 (POP)"| Worker
        Worker -->|"5.初始化"| Planner
        Planner -->|"6.下发检索指令"| Miner
        
        %% --- 核心检索逻辑变更 ---
        Miner <-->|"6a.API搜索"| Arxiv
        Miner <-->|"6b.RAG检索"| VectorDB
        
        Miner --> Builder
        Builder --> Auditor
        
        %% --- 核心容错循环 (红线) ---
        Auditor -.->|"格式错误/幻觉 (Retry)"| Builder
        linkStyle 13 stroke:#c62828,stroke-width:2px,color:red,stroke-dasharray: 5 5;
        
        %% --- 成功落地 ---
        Auditor -->|"7a.校验通过 (Write)"| Neo4j
        Auditor -.->|"7b.更新状态 (Success)"| Redis
    end

    %% --- 全局连线样式 ---
    linkStyle default stroke:#333,stroke-width:2px;
```

### 2.2 技术栈概览

#### 后端与架构 (Backend & Infrastructure)
| 模块 | 技术选型 | 技术方案说明 |
| :--- | :--- | :--- |
| **API 网关** | **FastAPI** (Python) | 采用高性能 ASGI 框架，利用 `async/await` 特性处理高并发长连接，自动生成 OpenAPI 规范文档。 |
| **消息队列** | **Redis** | 引入内存级中间件实现**异步解耦**，作为任务缓冲池，确保高并发下系统的稳定性。 |
| **容器编排** | **Docker Compose** | 采用云原生部署方案，通过声明式配置管理多容器生命周期，确保环境一致性。 |

#### 前端与可视化 (Frontend & Visualization)
| 模块 | 技术选型 | 技术方案说明 |
| :--- | :--- | :--- |
| **前端框架** | **React** + **Vite** | 基于组件化架构构建单页应用 (SPA)，实现数据与视图分离，提供流畅的用户交互体验。 |
| **图谱渲染** | **Apache ECharts** | 使用高性能可视化引擎渲染大规模力导向图，支持节点的高亮、折叠与动态交互。 |
| **UI 组件库** | **Ant Design** + **Framer Motion** | 采用企业级 UI 设计语言与 Framer Motion 动画库，构建具备磨砂玻璃质感 (Glassmorphism) 与流畅动效的沉浸式界面。 |

#### 智能体 (Agent System)
| 模块 | 技术选型 | 技术方案说明 |
| :--- | :--- | :--- |
| **Agent 编排** | **LangGraph** | 采用**有向有环图 (Cyclic Graph)** 架构编排智能体，支持“生成-校验-修正”的**自愈**流程。 |
| **图数据库** | **Neo4j** | 使用原生图数据库存储知识实体及其拓扑结构，利用 Cypher 语言高效执行多跳查询。 |
| **RAG 检索** | **ChromaDB** | 部署本地向量数据库支持 **RAG (检索增强生成)**，对教科书进行高维向量索引，弥补模型知识盲区。 |

---

## 3. 快速开始 (Quick Start)

本项目基于 Docker 构建，可实现一键部署。

### 前置要求
- Docker Desktop 或 Docker Engine
- Docker Compose

### 启动步骤

1. **克隆项目**
   ```bash
   git clone <repository_url>
   cd AutoKGS
   ```

2. **配置环境变量**
   复制示例配置并修改（如需使用 OpenAI API）：
  ```bash
  # --- Neo4j 数据库配置 ---
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=1234567888

  # --- OpenAI API 配置 ---
  OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  ```

3. **启动服务**
   ```bash
   docker-compose up --build -d
   ```

4. **访问服务**
   - **前端界面**: [http://localhost:5173](http://localhost:5173)
   - **后端 API**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Neo4j 控制台**: [http://localhost:7474](http://localhost:7474) (默认账号: neo4j / 密码见 .env)

### 停止服务
```bash
docker-compose down
```

---

## 4. 项目结构

```Plaintext
AutoKGS/
├── docker-compose.yml          # [核心] 容器编排配置
├── README.md                   # 项目文档
├── .env                        # 环境变量
├── .gitignore                        
│
├── docs/                    # [文档] 交付物
│
├── frontend/                # [服务1] 前端容器
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── node_modules/
│   └── src/
│       ├── components/
│       ├── api/
│       └── App.jsx
│       └── main.jsx
│
├── backend/                 # [服务2] 后端 API 容器
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置读取
│   ├── routers/
│   └── database/
│
├── agent_engine/            # [服务3] 智能体 Worker 容器
│   ├── Dockerfile              
│   ├── requirements.txt        
│   ├── worker_main.py          # 主程序
│   ├── config.py               
│   │
│   ├── textbooks/           # RAG源数据：存放 .pdf 教科书文件
│   │
│   ├── agents/              # 智能体逻辑
│   │   ├── planner.py          # 规划
│   │   ├── miner.py            # 混合调用 ArXiv 和 RAG
│   │   ├── builder.py          # 构建 JSON
│   │   └── auditor.py          # 校验 (负责打回重做)
│   │
│   ├── tools/               # 工具链
│   │   ├── search_arxiv.py     # ArXiv 论文搜索工具
│   │   └── rag_retriever.py    #  Chroma 本地教科书检索工具
│   │
│   ├── utils/               # 通用工具
│   │
│   └── prompts/             # 提示词迭代
│
├── neo4j_data/              # Neo4j 数据挂载
└── chroma_data/             # 向量数据库数据挂载 (防止重启后RAG失效)
```
## 5.数据格式
### 图数据格式：

```json
{
  "nodes": [
    {
      "id": "熵(Entropy)",
      "label": "熵",
      "group": "Physics",
      "size": 50,
      "info": "热力学中表示系统的混乱程度...",
      // ---【示例1：来自教科书 (RAG)】---
      "source_type": "textbook", 
      "source": "《复杂系统导论》 (Introduction to Complexity)", 
      "url": "", // 点击跳转到课本
      "confidence": 0.98
    },
    {
      "id": "信息不确定性(Uncertainty)",
      "label": "信息不确定性",
      "group": "Information Theory",
      "size": 40,
      "info": "信息论的核心概念...",
      // ---【示例2：来自论文 (ArXiv)】---
      "source_type": "paper",
      "source": "A Mathematical Theory of Communication",
      "url": "https://arxiv.org/abs/cs/9809005", // 点击跳转 ArXiv
      "confidence": 0.92
    }
  ],
  "links": [
    {
      "source": "熵(Entropy)",
      "target": "信息不确定性",
      "relation": "MATHEMATICAL_BASIS",
      "desc": "香农借鉴了玻尔兹曼公式...",
      // ---【关系引用】（如有）---
      "citation": "Shannon, C. E. (1948). A Mathematical Theory of Communication."
    }
  ]
}
```

### Redis格式：

#### 任务发布：

```json
{
  "task_id": "550e8400-e29b-41d4...", //UUID，唯一凭证
  "keyword": "熵",                    // 用户输入
  "params": {                         // (可选) 额外参数
    "depth": 3,                       // 搜索深度
    "language": "zh"
  },
  "created_at": 1709876543
}
```

### 任务状态格式：
*存入 Redis Key-Value (Key: `task:550e8400...`)* 后端接口会不断轮询读取这个 Key。

#### 1. 状态流转定义 (Step Definitions)
前端根据 `step_index` (0-4) 展示不同的加载动画步骤。后端需按照以下阶段更新 Redis：

| Step | Status | Progress | Message (示例) | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **0** | PROCESSING | 5 | "任务已发送至 Redis 队列..." | 初始状态，等待 Worker 领取 |
| **1** | PROCESSING | 20 | "AI Worker (Agent) 已接单..." | Worker 开始执行 |
| **2** | PROCESSING | 45 | "正在检索 ArXiv 和教科书..." | Miner Agent 进行混合检索 |
| **3** | PROCESSING | 70 | "正在提取实体与关系..." | LLM 阅读文本并抽取知识 |
| **4** | PROCESSING | 90 | "图谱构建完成，正在渲染..." | 校验通过，写入 Neo4j |
| **5** | SUCCESS | 100 | "Completed" | 任务彻底完成，返回结果 |

#### 2. JSON 示例

**进行中 (Processing):**
```json
{
  "status": "PROCESSING",
  "step_index": 2,       
  "progress": 45,
  "message": "正在检索 ArXiv 和教科书..."
}
```

**成功 (Success):**
```json
{
  "status": "SUCCESS",
  "step_index": 5,
  "progress": 100,
  "result_node_id": "Entropy", // 告诉后端去 Neo4j 查哪个主节点
  "message": "Completed",
  "completed_at": 1709876599
}
```

**失败 (Failed):**
```json
{
  "status": "FAILED",
  "error": "搜索超时，请稍后重试"
}
```


