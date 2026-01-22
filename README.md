# AutoKGS: 跨学科知识图谱智能体

## 1. 项目背景与目标

**痛点场景**：
在现代教育与科研中，知识碎片化现象严重。学生难以洞察不同学科间（如神经科学与深度学习、热力学与信息论）的内在关联，导致知识体系割裂。

**核心目标**：
构建一个基于多智能体（Multi-Agent）协作的系统，自动挖掘跨领域概念的桥梁，并构建可视化的知识图谱，帮助用户发现“远亲概念”的逻辑联系。

**功能清单**：

- **深度关联挖掘**：利用智能体在不同学科领域（数学、物理、社会学等）自动寻找相关概念。
- **自动化图谱构建**：从非结构化文本中提取实体及其关系，生成标准化的图结构数据。
- **混合检索增强 (RAG + Online)**：结合本地教科书知识库（RAG）与在线学术资源（ArXiv/Wikipedia），确保知识的广度与深度。
- **交互式可视化**：提供 Web 端动态交互界面，支持力导向图的拖拽、缩放与点击跳转。
- **多视图切换**：支持**知识图谱 (Knowledge Graph)** 与 **思维导图 (Mind Map)** 两种视图模式，满足不同场景下的知识探索需求。
- **幻觉校验机制**：引入`Query Agent(质量评估智能体)`和`Validator Agent(置信度打分智能体)`对生成内容评估是否需要联网增强和是否达到可以展示的置信度标准，拒绝大模型的幻觉影响。
- **证据与可信度呈现**：关系边展示 `desc/citation`，并以 `confidence` 强化高可信节点主干图。
- **筛选与导出**：支持主干图(设置置信度阈值)和探索层(展示全部节点)的切换，支持导出当前图谱 JSON 文件。
- **知识库导入**：提供工具自动扫描并导入 EPUB/MOBI 格式教科书到向量数据库。

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
    FE -->|"13.渲染图谱展示"| User

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
        
        API <-->|"11.读取图谱数据 (Query)"| Neo4j
        API -->|"12.返回完整数据"| FE
    end

    %% --- 外部学术资源 ---
    Arxiv(("外部学术资源<br/>(ArXiv API 查论文)")):::ext

    %% --- Member B: 智能体策略 (Agent Strategy) ---
    subgraph GroupB ["Member B: 智能体策略 (Agent Pipeline)"]
        direction TB
        Worker["Worker 容器 (Agent Runner)"]:::eng
        
        subgraph Pipeline ["Agent Pipeline"]
            Planner("Planner Agent<br/>(路径规划)"):::ai
            Miner("Miner Agent<br/>(混合检索)"):::ai
            Query("Query Agent<br/>(质量评估)"):::ai
            MinerOnline("Miner Online<br/>(联网兜底)"):::ai
            Validator("Validator Agent<br/>(置信度打分)"):::ai
            Relation("Relation Agent<br/>(跨学科关联)"):::ai
        end
        
        Redis -->|"4.领取任务 (POP)"| Worker
        Worker -->|"5.启动"| Planner
        Planner -->|"6.生成关键词与领域"| Miner
        
        %% --- 核心检索逻辑变更 ---
        Miner <-->|"7a.本地 RAG"| VectorDB
        Miner --> Query
        
        Query -->|"7b.结果不足?"| MinerOnline
        Query -.->|"足够"| Validator
        
        MinerOnline <-->|"7c.外部API (ArXiv/Wiki)"| Arxiv
        MinerOnline --> Validator
        
        Validator -->|"8.节点打分"| Relation
        
        %% --- 关系构建与落地 ---
        Relation -->|"9.生成 Links"| Worker
        Worker -->|"10a.写入图谱"| Neo4j
        Worker -.->|"10b.更新状态"| Redis
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

| 模块           | 技术选型            | 技术方案说明                                                 |
| :------------- | :------------------ | :----------------------------------------------------------- |
| **Agent 编排** | **Custom Workflow** | 采用线性工作流 + 并发执行（Planner → Miner/MinerOnline → Validator → Relation）架构，支持多线程并发检索。 |
| **大模型支持** | **ECNU-LLM / Kimi** | 支持接入 ECNU 校内 LLM 或 Moonshot AI (Kimi) API 进行语义理解与生成。 |
| **图数据库**   | **Neo4j**           | 使用原生图数据库存储知识实体及其拓扑结构，利用 Cypher 语言高效执行多跳查询。 |
| **RAG 检索**   | **ChromaDB**        | 部署本地向量数据库支持 **RAG (检索增强生成)**，对教科书进行高维向量索引，弥补模型知识盲区。 |


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
   由于 `.env` 文件包含敏感信息，通常不包含在代码仓库中。你需要手动创建 `.env` 文件。

   在项目根目录下创建 `.env` 文件，并填入以下内容：

   ```bash
   # --- Neo4j 数据库配置 ---
   NEO4J_URI=bolt://neo4j:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password # 请修改为你想要的密码
   
   # --- Redis 配置 ---
   REDIS_HOST=redis
   REDIS_PORT=6379
   
   # --- ChromaDB 配置 ---
   CHROMA_SERVER_HOST=chromadb
   CHROMA_SERVER_PORT=8000
   
   # --- LLM 配置 ---
   
   # 1. ECNU LLM (推荐，用于本地 RAG 和逻辑处理)
   LLM_API_KEY=your_ecnu_api_key
   LLM_API_BASE=https://api.ecnu.edu.cn/v1
   EMBEDDING_MODEL=ecnu-embedding-small
   
   # 2. Kimi (Moonshot AI) (用于联网检索兜底)
   KIMI_API_KEY=sk-xxxxxxxx
   KIMI_API_BASE=https://api.moonshot.cn/v1
   ```

3. **启动服务**

   ```bash
   docker-compose up --build -d
   ```

4. **访问服务**

   - **前端界面**: [http://localhost:5173](http://localhost:5173)
   - **后端 API**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Neo4j 控制台**: [http://localhost:7474](http://localhost:7474) (账号: neo4j / 密码: 你在.env中设置的密码)
   - **ChromaDB**: [http://localhost:8001](http://localhost:8001)

### 数据导入 (RAG 增强)

为了让 AI 拥有更专业的学科知识，你可以导入本地教科书数据。

**数据资源：**
我们提供了一份基础的学科分类教科书数据集：

*   **下载链接**: https://pan.baidu.com/s/1aOxGAS_UwNEWgix-l9Y4wA?pwd=6ju3 
*   **提取码**: 6ju3

还提供了经处理后的教科书的向量集：

- **下载链接**：https://pan.baidu.com/s/1wIaPRWgOmV66hAy9oRtgBQ?pwd=wvhy
- **提取码**：wvhy

**导入方式（任选其一）：**

**方式 A：扫描教科书文件（链接可能因版权问题而失效，此时需要切换方式B或者联系我们获取）**
1. 下载并解压 `data.7z`。
2. 将解压得到的 `data` 文件夹（包含 `.epub` / `.mobi`）放在项目根目录的 `/data`。  
   *(注：`/data` 已映射到容器内 `/app/data`)*
3. 执行导入脚本：
   ```bash
   docker compose exec worker bash
   python -m tools.ingest_books
   ```
   *脚本会递归扫描 `/app/data` 并写入 ChromaDB。*

**方式 B：导入 ChromaDump（快速恢复）**
1. 将 `chroma_dump.json` 放到 `/data`（容器内路径为 `/app/data/chroma_dump.json`）。
2. 执行导入脚本：
   ```bash
   docker compose exec worker bash
   python -m tools.import_chromadb
   ```
   *脚本会按 collection 批量 upsert 到 ChromaDB。*
---
## 4. 项目结构

```Plaintext
AutoKGS/
├── docker-compose.yml          # [核心] 容器编排配置
├── README.md                   # 项目文档
├── .env                        # 环境变量
├── .gitignore                        
│
├── frontend/                # [服务1] 前端容器 (React + Vite)
│   ├── Dockerfile
│   ├── src/
│   │   ├── components/
│   │   ├── api/
│   │   ├── useGraphOption.js   # 图谱配置
│   │   ├── useMindMapOption.js # 思维导图配置
│   │   └── App.jsx
│   └── ...
│
├── backend/                 # [服务2] 后端 API 容器 (FastAPI)
│   ├── Dockerfile
│   ├── main.py                 # FastAPI 入口
│   ├── routers/                # 路由定义 (Task, Graph)
│   └── database/               # 数据库连接工具
│
├── agent_engine/            # [服务3] 智能体 Worker 容器 (Python)
│   ├── Dockerfile              
│   ├── worker_main.py          # Worker 主程序 (监听 Redis)
│   ├── workflow.py             # Agent 工作流编排
│   ├── config.py               
│   │
│   ├── agents/              # 智能体实现
│   │   ├── planner.py          # 规划 Agent
│   │   ├── miner.py            # 挖掘 Agent (RAG)
│   │   ├── miner_online.py     # 联网 Agent
│   │   ├── query.py            # 质检 Agent
│   │   ├── validator.py        # 验证 Agent
│   │   └── relation.py         # 关系 Agent
│   │
│   ├── tools/               # 工具链
│   │   ├── ingest_books.py     # 图书导入工具
│   │   ├── ecnu_llm.py         # LLM 封装
│   │   ├── search_arxiv.py     # ArXiv 工具
│   │   └── rag_retriever.py    # RAG 检索器
│   │
│   └── prompt/              # Prompt 模板
│
├── neo4j_data/              # Neo4j 数据持久化
├── chroma_data/             # ChromaDB 数据持久化
└── redis_data/              # Redis 数据持久化
```




