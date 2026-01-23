# 跨学科知识图谱智能体（Cross-Disciplinary Knowledge Graph Agent）
**云计算期末大作业｜智能体云原生开发（命题三）**

本项目面向“学习中的知识碎片化与跨学科迁移困难”问题：用户输入一个核心概念（如 *熵/Entropy*、*递归/Recursion*），系统通过**多阶段 LLM 智能体工具链**（Planner → Retriever → Extractor → Checker）**强制在多学科领域检索与抽取相关概念**，生成结构化知识图谱（节点/边/证据/置信度/校验状态），通过 **Check Layer** 降低幻觉与错误关联，并将结果持久化至 **Neo4j**，最终在 Web 端以 **React + ECharts** 进行可交互、可解释的可视化展示。  
项目支持 **Docker Compose 一键部署复现**（frontend/backend/redis/neo4j），具备完整工程闭环。

## ✨ 核心功能

### 1）跨学科强制扩展（Planner）
- 默认覆盖学科域：**Mathematics / Physics / Computer Science / Biology / Economics**（外加 Core/Bridge）
- Planner 为每个领域生成 **3–6 条领域化检索 query**，避免“只做同义词搜索”。

### 2）证据驱动的图谱抽取（Retriever + Extractor）
- Retriever 从外部知识源（如 Wikipedia / arXiv / Search API 或 seed 语料）获取分领域证据片段（passages）。
- Extractor 基于证据输出**标准图谱 JSON**：
  - `nodes`: id/name/domain/definition/confidence
  - `edges`: relation/explanation/evidence/confidence/checked/check_reason/flags

### 3）Check Layer 可信度校验（Checker）
- **Schema 校验 + light fix**：保证结构化输出格式稳定
- **证据一致性校验**：
  - 证据不足则 `checked=false`，并给出 `check_reason`
  - 必要时将关系降级为更弱的 `related_to`
- 冲突边（Conflict）标记，支持前端过滤与高亮。

### 4）云原生工程闭环
- **Docker Compose** 编排四个核心服务：
  - `frontend`（React/Vite）
  - `backend`（FastAPI）
  - `redis`（任务状态/日志缓存）
  - `neo4j`（知识图谱持久化）
- healthcheck + 依赖顺序确保启动稳定。


## 快速开始（Docker 一键启动）

在项目根目录执行：

```bash
docker compose -p xkg up -d --build
```

启动后访问：
- **Web UI**：`http://localhost:5173`
- **Backend API (Swagger)**：`http://localhost:8000/docs`
- **Neo4j Browser**：`http://localhost:7474`（账号 `neo4j` / 密码 `neo4j_password`）


## 使用说明

1. 打开 Web UI，输入概念词（例如 `Entropy` 或 `熵`），点击 Generate
2. 等待 Job 完成后会自动加载图谱
3. 点击节点查看详情与证据；点击 Expand 进行二跳扩展
4. 使用 Filters：
   Domain / Relation / Checked / Confidence 阈值
5. 使用 Expand (2-hop) 扩展图谱

## 项目结构

- `backend/`：FastAPI + Agent Orchestrator + Redis/Neo4j
- `frontend/`：React + ECharts 图谱可视化
- `docker-compose.yml`：一键启动 Redis / Neo4j / backend / frontend

