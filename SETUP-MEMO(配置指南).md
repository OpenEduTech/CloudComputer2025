# SmartLecPPTKiller 提交版 GitHub 仓库配置与操作步骤

2026-01

---

## 0. 本文的意义

按本文完成后，你应能做到：
- 通过 Docker Compose 一键启动四个服务：`frontend`、`backend`、`chromadb`、`redis`。
- 在浏览器打开前端页面并完成基本调用：上传并解析 PPT/PDF、知识扩充、出题判卷、错题本与小灶纠偏。

---

## 1. 前置条件

### 1.1 必需软件

- Git
- Docker Desktop（含 Docker Compose）

若需要本地“非 Docker”开发（可选）：
- Node.js 18+
- Python 3.11+

### 1.2 关于密钥与仓库安全

- 本仓库已在 `.gitignore` 中忽略 `.env`（见 `.gitignore` 的 Environment 部分）。
- 正确做法：只在本机创建 `.env`，不要提交到 GitHub；也不要在文档/截图中展示真实 Key。

---

## 2. 获取代码

在你希望存放项目的目录执行：

```bash
git clone <repository-url>
cd main
```

说明：本文所有命令均以仓库 `main/` 目录为工作目录。

---

## 3. 环境变量配置（.env）

### 3.1 创建 .env

在仓库根目录（`main/`）执行：

```bash
# Windows PowerShell 也可手动复制文件
cp .env.example .env
```

### 3.2 必配项（只写到 .env，不要写进仓库）

打开 `.env`，至少确保以下字段已配置：

- `DEEPSEEK_API_KEY`：你的 DeepSeek API Key（必填）
- `DEEPSEEK_API_BASE`：DeepSeek API Base URL（仓库当前默认是带 `/v1` 的形式）
- `DEEPSEEK_MODEL`：默认 `deepseek-chat`（可按需调整）
- `DEEPSEEK_EMBEDDING_MODEL`：默认 `deepseek-embedding`

建议写法示例（示例中的值均为占位，不要照抄为真实 Key）：

```dotenv
DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_EMBEDDING_MODEL=deepseek-embedding
```

### 3.3 可选项（按需要开启/关闭）

这些开关在 `.env.example` 中已给出：

- OCR：`OCR_ENABLED`、`OCR_SEMANTIC_ENABLED`、`TESSERACT_CMD`
- 目录概括：`OUTLINE_SUMMARY_ENABLED`
- LLM 输出校验：`LLM_VALIDATION_ENABLED`
- 外部检索开关：`WIKIPEDIA_API_ENABLED`、`ARXIV_API_ENABLED`、`SEMANTIC_SCHOLAR_API_ENABLED`、`OPENALEX_API_ENABLED`、`STACKEXCHANGE_API_ENABLED`、`BING_SEARCH_API_ENABLED`、`GOOGLE_CSE_API_ENABLED`

注意：外部检索里有部分服务需要额外 Key（如 Bing/Google CSE），未配置则对应能力不可用或返回空结果，这属于预期行为。

---

## 4. Docker Compose 一键启动（推荐、最贴近演示/交付）

在 `main/` 目录执行：

```bash
docker-compose up -d --build
```

### 4.1 端口与访问入口（以仓库 `docker-compose.yml` 为准）

- 前端：`http://localhost:8080`
- 后端：`http://localhost:8002`
- 后端 Swagger：`http://localhost:8002/docs`
- ChromaDB（如需直接访问）：`http://localhost:8001`
- Redis：`localhost:6379`

### 4.2 前端 API 代理说明（避免跨域与重复配置）

- 前端容器采用 Nginx 提供静态资源，并在 `frontend/nginx.conf` 中将 `/api/` 代理到后端容器 `backend:8000`。
- 因此前端在容器模式下使用默认的相对路径 `/api` 即可，无需把后端 URL 写死进前端代码。

### 4.3 验证清单

1) 打开 `http://localhost:8080` 能看到前端页面。
2) 打开 `http://localhost:8002/health` 返回 `status: healthy`。
3) 打开 `http://localhost:8002/docs` 能看到 FastAPI 的 OpenAPI 文档。

---

## 5. 本地开发模式（不推荐）

当你希望改代码并热更新调试时，建议使用“依赖服务用 Docker，本体服务本地跑”的方式。

### 5.1 仅启动依赖（ChromaDB + Redis）

```bash
docker-compose up -d chromadb redis
```

### 5.2 后端本地运行（FastAPI）

参考 `docs/LOCAL_SETUP.md`：

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

验证：
- `http://localhost:8000/docs`
- `http://localhost:8000/health`

### 5.3 前端本地运行（Vite）

```bash
cd frontend
npm install
npm run dev
```

说明：
- `frontend/vite.config.js` 内置了 `/api` 代理：默认目标是 `http://localhost:8000`。
- 若你把后端跑在别的地址/端口，可通过环境变量 `VITE_API_BASE_URL` 调整（不要提交含私密信息的环境文件）。

---

## 6. OCR 配置说明

### 6.1 Docker 模式

- 后端 Dockerfile 已安装 `tesseract-ocr` 与中文语言包 `tesseract-ocr-chi-sim`（见 `backend/Dockerfile`）。
- 只需在 `.env` 中开启：
  - `OCR_ENABLED=true`
  - `OCR_SEMANTIC_ENABLED=true`：启用“基于 OCR 文本的语义解说”

### 6.2 本地非 Docker 模式

- 你需要在本机自行安装 Tesseract。
- Windows 场景下，如需指定 tesseract 可执行文件路径，可在 `.env` 中设置 `TESSERACT_CMD`。

---

## 7. 常见问题

### 7.1 LLM/Embedding 调用失败

- 检查 `.env` 的 `DEEPSEEK_API_KEY` 是否正确配置（不要把 Key 提交到仓库）。
- `backend/app/core/config.py` 会将 `DEEPSEEK_API_BASE` 自动规范到以 `/v1` 结尾；建议保持 `.env` 中也使用带 `/v1` 的形式，减少歧义。

### 7.2 前端请求后端失败 / 404

- Docker 模式：优先确认 Nginx 代理是否生效（`frontend/nginx.conf` 将 `/api/` 代理到 `backend:8000`）。
- 本地开发模式：Vite 代理默认指向 `http://localhost:8000`，请确保后端确实跑在该端口。

### 7.3 上传文件大小限制

- Nginx 配置中 `client_max_body_size 60m`（见 `frontend/nginx.conf`）。
- 后端限制由 `.env` 的 `MAX_UPLOAD_SIZE` 控制（默认 50MB，见 `.env.example`）。

---

## 8. 碎碎念：小建议

- 把“最快启动路径”放在仓库 README 顶部：`cp .env.example .env` + `docker-compose up -d --build`。
- 强调 `.env` 不要提交：仓库已通过 `.gitignore` 做了保护，但团队协作时仍应明确规则。
- 演示前做一次健康检查：`/health` 与 `/docs` 能打开，再演示前端的完整链路。
