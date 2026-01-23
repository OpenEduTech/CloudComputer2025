# 依赖配置文件与环境配置指南

本指南面向 **Windows + PowerShell**，目标是让非开发同学也能独立完成环境配置与运行。

## 1. 依赖配置文件说明（必须读）

**`requirements.txt`**
- **作用**：Python 依赖清单，包含 FastAPI、LangChain、Redis 客户端等。
- **使用方式**：本地运行时执行 `pip install -r requirements.txt`。

**`Dockerfile`**
- **作用**：构建 API 服务镜像，统一运行环境（Python 3.11 + 依赖）。
- **特点**：镜像内不需要本地 Python 环境，避免“环境不一致”导致运行失败。

**`docker-compose.yml`**
- **作用**：启动 **API 服务 + Redis** 的组合编排。
- **说明**：通过 `docker compose up --build` 一键启动两项服务。

**`.env.example`**
- **作用**：示例环境变量，包含模型密钥与运行参数。
- **说明**：复制为 `.env` 后填写真实 API Key。

## 2. 本地运行（不使用 Docker）

### 2.1 先决条件
- Python 版本：**3.11**
- 允许执行 PowerShell 脚本（如有权限限制，需管理员执行 `Set-ExecutionPolicy RemoteSigned`）

### 2.2 创建虚拟环境
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2.3 安装依赖
```powershell
pip install -r requirements.txt
```

### 2.4 配置环境变量
```powershell
Copy-Item .env.example .env
notepad .env
```

**`.env` 关键参数说明**
- **`LLM_API_KEY`**：大模型平台密钥（必须填写）
- **`LLM_BASE_URL`**：兼容 OpenAI API 的地址
- **`LLM_MODEL`**：模型名称（如 deepseek-chat）
- **`LLM_TEMPERATURE`**：生成随机度（建议 0.2~0.5）
- **`REDIS_URL`**：Redis 地址（本地可用 `redis://127.0.0.1:6379/0`）
- **`MAX_UPLOAD_MB`**：PDF 上传大小限制（默认 20）

### 2.5 启动服务
```powershell
uvicorn app.main:app --reload
```

访问：
- 主页：`http://127.0.0.1:8000/`
- 错题本：`http://127.0.0.1:8000/wrongbook`
- API 文档：`http://127.0.0.1:8000/docs`

## 3. Docker 运行（推荐）

### 3.1 先决条件
- 安装 Docker Desktop
- 确保 Docker Desktop 运行中

### 3.2 启动
```powershell
docker compose up --build
```

启动后请直接在浏览器访问：
- 主页：`http://127.0.0.1:8000/`
- 错题本：`http://127.0.0.1:8000/wrongbook`
- API 文档：`http://127.0.0.1:8000/docs`

### 3.3 停止并清理
```powershell
docker compose down -v
```

## 4. 常见问题与排查

**Q1：上传 PDF 提示“文件不是有效的 PDF”**
- 检查文件是否为真实 PDF，而非改后缀的文件。

**Q2：上传报“超过大小限制”**
- 调小 PDF 或在 `.env` 中增大 `MAX_UPLOAD_MB`。

**Q3：判卷/出题失败**
- 多数为模型输出格式错误或密钥无效，检查 `.env` 中 `LLM_API_KEY`。
- 若仍失败，查看 `data/llm_raw.txt` 或 `data/llm_grade_raw.txt`。

**Q4：本地 Redis 报错**
- 本地模式需要 Redis 服务；或改用 Docker 运行。
