# 跨学科知识图谱 — 本地与 Docker 部署说明

本仓库包含一个前端（React + Vite）、后端（FastAPI）、Agent（LLM 驱动的多步骤构建服务）、Redis（缓存）与 Neo4j（图数据库）的完整项目。此文档目的是帮助开发者和运维人员在本地或使用 Docker Compose 时快速上手，并包含常见故障排查步骤。

> 注意：仓库已去掉敏感密钥。请使用 `dev.env`（未提交）放置真实密钥，仓库中提供 `dev.env.example` 作为模板。

目录
- 快速开始（Docker）
- 本地开发（无 Docker）
- 端口与容器内/外 URL 说明
- 健康检查与日志
- 常见问题与故障排查
- 安全建议（密钥与环境变量）
- 其他（初始化 Neo4j、CI 建议）


## 快速开始（使用 Docker Compose）

前提条件
- 已安装 Docker Desktop（含 docker-compose v2 或 v1 均可）
- 至少 8GB 可用内存（Neo4j 与前端/后端同时运行时）

步骤
1. 克隆仓库并进入项目根目录：
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```
2. 从示例文件复制环境变量并在本地填写真实密钥：
   ```bash
   cp dev.env.example dev.env
   # 编辑 dev.env，把 DEEPSEEK_API_KEY 替换为你的真实 key（仅保存在本地）
   ```
3. 启动服务（开发模式，compose 已为前端使用卷挂载以支持热重载）：
   ```bash
   docker-compose up --build -d
   ```
4. 查看运行状态：
   ```bash
   docker-compose ps
   ```
5. 查看日志（实时）：
   ```bash
   docker-compose logs -f backend
   docker-compose logs -f agent-service
   docker-compose logs -f frontend
   ```
6. 若需停止并清理（包括卷）：
   ```bash
   docker-compose down --volumes
   ```

访问 `http://localhost:8080` 即可访问可视化界面。
注意：第一次启动 Neo4j 可能需要额外时间完成初始化，health check 可能在容器启动后短时间返回 unhealthy，稍等几分钟再查看即可。

## 本地开发（不使用 Docker）

### 后端（FastAPI）
1. 进入后端目录并创建虚拟环境：
   ```bash
   cd back
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\\Scripts\\activate    # Windows PowerShell
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 复制 `dev.env.example` 为 `dev.env` 并配置变量（同上）。
4. 运行：
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Agent 服务（独立运行）
1. 进入 `back/agent-service`：
   ```bash
   cd back/agent-service
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp ../dev.env.example dev.env
   # 编辑 dev.env，添加真实的 DEEPSEEK_API_KEY 等
   uvicorn api:app --host 0.0.0.0 --port 8001 --reload
   ```

### 前端（React + Vite）
1. 进入项目根目录：
   ```bash
   npm install
   npm run dev
   ```

## 端口与容器内/外 URL 说明
- 前端 (容器外): http://localhost:3000
- 后端 (容器外): http://localhost:8080 -> 映射到容器内 `8000`
- Agent (容器外): http://localhost:8001 -> 映射到容器内 `8001`
- Neo4j 浏览器: http://localhost:7474
- Neo4j Bolt: bolt://localhost:7687

容器内互联的地址（在容器内部，服务通过 Compose 网络互相访问）：
- 后端访问 Agent: `http://agent-service:8001`
- 前端在容器内访问后端（容器内）: `http://backend:8080`（compose environment 指定）

常见混淆：
- 在宿主机器的浏览器中访问后端请使用 `http://localhost:8080`，而在容器内从前端访问后端应使用 `http://backend:8080`（容器名解析）。

## 健康检查与 readiness
- Compose 中已为 backend/agent/neo4j/redis 配置 healthcheck。若某服务显示 `unhealthy`：
  1. 查看容器日志：`docker-compose logs <service> --tail 200`
  2. 查看 health 细节：`docker inspect --format='{{json .State.Health}}' <container>`
  3. 对 Neo4j，首次启动可能需要时间，耐心等待并查看 `/logs` 卷。

## 常见故障排查
- 问题：前端显示 mock 数据或一直等待
  - 检查后端/agent 是否 healthy（`docker-compose ps`）。
  - 查看后端日志（`docker-compose logs backend --tail 200`）寻找 `mock` 或 `fallback` 关键词。
  - 确认 `dev.env` 中 `USE_MOCK` 是否被设置为 `True`。
  - 确认后端能访问 Agent：在后端容器内执行 `curl http://agent-service:8001/healthz`。

- 问题：Agent 报错与 LLM 相关（JSON 解析、超时）
  - 检查 `DEEPSEEK_API_KEY` 是否有效且已正确放入容器的环境变量（`docker-compose exec agent-service printenv | grep DEEPSEEK`）。
  - 检查 deepseek 是否还有余额。
  - 检查 Agent 日志中的 `Unclosed JSON object` 或 `JSONDecodeError`，这是 LLM 返回格式问题，Agent 已实现降级到 mock 的保护逻辑。
  - 若出现 SSL/连接错误，确认 host 能访问 `DEEPSEEK_BASE_URL` 并且网络/防火墙允许外发请求。若连接错误，可以刷新、反复再尝试几遍，因为连接效果不是完全稳定的。

- 问题：Neo4j 连接失败
  - 检查 `NEO4J_URI`、`NEO4J_USERNAME`、`NEO4J_PASSWORD` 是否一致。
  - 查看 Neo4j 日志：`docker-compose logs neo4j --tail 200`。
  - 确认 Neo4j 插件（apoc）是否按需安装。


# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/temp/1

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`

## 项目文件结构（概览与说明）
下面列出仓库主要目录与文件及其作用，便于其他协作者快速理解项目布局。

- **根目录**
  - `README.md`：本文件，包含启动、调试与项目说明。
  - `dev.env.example`：环境变量示例（不含密钥）。请复制为本地 `dev.env` 并填写真实密钥。
  - `docker-compose.yml`：开发时的 Compose 编排（包含 frontend/backend/agent/neo4j/redis）。
  - `docker-compose.prod.yml`：生产部署时的示例 Compose（如存在）。
  - `Dockerfile`：前端 multi-stage 构建与开发镜像定义（根目录用于 frontend 构建）。
  - `nginx.conf`：生产镜像中 nginx 配置（前端静态站点）。
  - `package.json` / `package-lock.json`：前端依赖管理与脚本。
  - `tsconfig.json` / `vite.config.ts`：前端 TypeScript 与 Vite 配置。
  - `index.html` / `index.tsx`：前端入口。
  - `geminiService.ts`：前端与后端/agent 的 API 封装与降级逻辑。
  - `entropy.json`, `least_squares.json`, `metadata.json`：示例数据与元信息（供前端或测试使用）。

- **`components/`**
  - `ContextScreen.tsx`：核心的知识图谱可视化与交互组件（节点布局、渲染、左侧详情面板等）。
  - `SearchScreen.tsx`：搜索/输入界面组件（触发查询）。
  - `Icons.tsx`：图标组件集合。
  - `DetailOverlay.tsx`：曾用于展示节点详情的组件（如已删除或未使用会在代码中被移除）。

- **`back/`（后端主实现）**
  - `Dockerfile`：后端镜像构建（用于 `backend` 服务）。
  - `requirements.txt`：后端 Python 依赖清单。
  - `mock_data/`：早期的 mock 示例数据（可用于离线调试，仓库中可选保留）。
  - **`back/app/`**：FastAPI 应用主逻辑
    - `main.py`：后端应用入口（uvicorn 可载入）。
    - `api/graph.py`, `api/task.py`：对外 HTTP 接口（图谱生成、任务状态等）。
    - `services/graph_service.py`, `services/task_service.py`：业务逻辑实现（与 Neo4j/Redis 的交互）。
    - `core/config.py`：配置读取与环境变量管理。
    - `models/graph.py`：后端内部的数据模型定义。
  - **`back/agent-service/`**：Agent 服务（调用 LLM 的多步骤流水线）
    - `api.py`：Agent 的 FastAPI 应用入口（`uvicorn api:app`）。
    - `agent_pipeline.py`：多步解析/生成/修复/合并的管道逻辑（Step0..Step4）。
    - `llm_client.py`：与 DeepSeek（或其他 OpenAI-compatible API）通信的客户端封装。
    - `prompts/`：用于构造 LLM 请求的提示模板文件。
    - `step4_postprocess.py`：LLM 输出后处理（结构化、修复、过滤等）。

- **`backend/`（历史/副本）**
  - 该目录曾为 `back/` 的副本，仓库已清理大部分重复内容。若你仍看到 `backend/`，它可能只剩下少量缓存或 pyc 文件，可删除或忽略。

- 其他辅助脚本与文件
  - `start-dev.sh`：用于在本地脚本化启动 Compose 的辅助脚本（可选）。
  - `test-api-key.sh`、`test-integration.sh`：早期测试脚本（若已删除则不再存在）。
  - `openapi.agent.yaml` / `openapi.backend.yaml`：API OpenAPI 规格（用于文档与客户端生成）。
