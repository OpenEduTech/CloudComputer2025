# 机器学习学习评估与巩固智能体（第029组）

本项目对应命题二：基于机器学习教材 PDF，自动出题、判卷并生成错题本与复习建议。

## 主要功能（MVP）
- PDF 解析与切分
- 自动出题（选择题 + 简答题）
- 智能判卷（对错 + 解析）
- 错题本持久化（Redis）
- 轻量检索增强：出题与判卷自动挑选相关片段，提高证据质量

## 技术栈
- Python + FastAPI
- LangChain + LangGraph
- Redis
- Docker / docker-compose

## 本地运行
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LLM_API_KEY="你的_api_key"
uvicorn app.main:app --reload
```

## Docker 运行
```powershell
docker compose up --build
```

## 环境变量
复制 `.env.example` 为 `.env` 并填写配置，修改后需要重启服务。
```powershell
Copy-Item .env.example .env
notepad .env
```

参数说明：
- `LLM_API_KEY`：大模型平台的真实密钥
- `LLM_BASE_URL`：兼容 OpenAI API 的基础地址
- `LLM_MODEL`：模型名称（如 deepseek-chat）
- `LLM_TEMPERATURE`：生成随机度（建议 0.2~0.5）
- `REDIS_URL`：Redis 连接地址（默认自动识别本地/Docker）
  - 本地运行：`redis://127.0.0.1:6379/0`
  - Docker 运行：`redis://redis:6379/0`
- `USE_LANGGRAPH`：是否使用 LangGraph（预留开关）

## 检索增强说明
系统在出题与判卷时，会根据教材片段与问题文本进行轻量检索，挑选相关片段传入 LLM：
- 出题：根据高频关键词挑选代表性片段作为上下文
- 判卷：根据问题与参考答案挑选相似片段作为参考资料

## API 简表
- `GET /sessions`：会话列表
- `POST /sessions`：上传 PDF 并创建会话
- `DELETE /sessions/{session_id}`：删除会话
- `POST /questions`：生成题目
- `POST /grade`：判卷并记录错题
- `GET /wrongbook/all`：查询全局错题本
- `GET /records/{session_id}`：获取会话最近一次题目/作答/判卷

## 前端入口
- `/`：主页
- `/wrongbook`：错题本页

## 最小测试流程
1. 启动服务后访问 `GET /health`。
2. `POST /sessions` 上传 PDF，获得 `session_id`。
3. `POST /questions` 传入 `session_id` 生成题目。
4. `POST /grade` 传入题目与答案进行判卷。
5. `GET /wrongbook/all` 查看错题本。
6. 主页空状态提示应随步骤自动切换（未生成题目/等待判卷）。

## 文档
- `docs/ARCHITECTURE.md`：架构与数据流
- `docs/WORKSPLIT.md`：分工说明
- `docs/DEMO_SCRIPT.md`：演示脚本
