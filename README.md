# CloudComputer2025 - 跨学科知识图谱生成系统

本项目是一个基于云原生架构和 LLM Agent 的跨学科知识图谱生成系统。通过多智能体协作（Multi-Agent Collaboration），实现从并行网络搜索、知识抽取到图谱构建的全流程自动化。

## 项目分工 (Group 5)

*   **陈子谦**：前端开发与架构设计
    *   负责 Vue3 前端交互界面、D3.js 力导向图可视化。
    *   整体系统架构设计与 Docker 容器化编排。
*   **李则言**：Agent 并行搜索
    *   基于 LangGraph 构建搜索智能体状态机。
    *   实现多学科概念的并发搜索与验证策略。
*   **李佳亮**：LightRAG 知识图谱构建
    *   集成 LightRAG 框架，负责实体与关系的深度抽取。
    *   实现 Neo4j 图数据库的数据存储与同步。

## 技术栈

*   **前端**: Vue 3, Vite, D3.js, Pinia
*   **后端**: Python 3.13+, FastAPI, LangGraph, LightRAG, Neo4j Driver
*   **基础设施**: Docker, Docker Compose, Neo4j, Redis

## 项目结构概览

```bash
CloudComputer2025/
├── backend/                # 后端服务 (FastAPI + Agents)
│   ├── central_agent/      # 核心协调 Agent
│   ├── search_agent/       # 搜索 Agent (LangGraph)
│   ├── knowledge_engine/   # 知识处理引擎 (LightRAG)
│   └── main.py             # 入口文件
├── frontend/               # 前端应用 (Vue3)
├── data/                   # 数据持久化目录
│   ├── documents/          # 原始文档
│   ├── graphs/             # 生成的图谱 JSON 数据
│   └── neo4j_data/         # Neo4j 数据库文件
├── docker-compose.yml      # 容器编排文件
└── TECHNICAL_DOCUMENT.md   # 详细技术文档
```

## 快速配置与启动

### 1. 环境要求
*   Docker & Docker Compose

### 2. 配置环境变量
在项目根目录下复制或创建 `.env` 文件，填入以下配置：

```ini
# --- LLM 服务配置 ---
LLM_API_KEY=your_key_here              # 推荐 DeepSeek 或 OpenAI
LLM_BASE_URL=https://api.deepseek.com  # API 端点
LLM_MODEL=deepseek-chat

# --- 搜索服务配置 ---
OPENAI_API_KEY=your_openai_key         # Search Agent 可能需要
TAVILY_API_KEY=your_tavily_key         # 用于 Tavily 搜索服务

# --- 数据库配置 ---
NEO4J_PASSWORD=your_secure_password    # 设置 Neo4j 密码
```

### 3. 启动服务
在根目录下运行：

```bash
docker-compose up -d --build
```

### 4. 访问服务
服务启动后，可以通过以下地址访问：
*   **Web 前端**: [http://localhost:3000](http://localhost:3000)
*   **API 文档 (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Neo4j 浏览器**: [http://localhost:7474](http://localhost:7474)
