# 机器学习学习评估与巩固智能体（第029组）

本项目对应命题二：基于机器学习教材 PDF，自动出题、判卷并生成错题本与复习建议。

## 主要功能（MVP）
- PDF 解析与切分
- 动态出题（选择题 + 简答题）
- 智能判卷（对错 + 解析）
- 错题本持久化（Redis）
- 可选使用 LangGraph 组织流程

## 技术栈
- Python + FastAPI
- LangChain + LangGraph
- Redis
- Docker / docker-compose

## 本地运行
```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
$env:LLM_API_KEY="你的_api_key"
uvicorn app.main:app --reload
```

## Docker 运行
```powershell
docker compose up --build
```

## 环境变量
复制 `.env.example` 为 `.env` 并填写配置。

## API 简要
- `POST /sessions`：上传 PDF 并创建会话
- `POST /questions`：生成题目
- `POST /grade`：判卷并记录错题
- `GET /wrongbook/{session_id}`：查询错题本

## 最小测试流程
1. 启动服务后访问 `GET /health`。
2. `POST /sessions` 上传 PDF，获取 `session_id`。
3. `POST /questions` 传入 `session_id` 生成题目。
4. `POST /grade` 传入题目与答案进行判卷。
5. `GET /wrongbook/{session_id}` 查询错题本。
