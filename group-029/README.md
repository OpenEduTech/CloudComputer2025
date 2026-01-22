# 学习评估与巩固智能体（第029组）

面向任意学习资料（PDF/文本/转写文本）的学习评估系统：支持自动出题、判卷、错题本与个性化纠偏，并提供对话式问答入口。

## 快速链接
- 前端主页：http://127.0.0.1:8000/
- 错题本页：http://127.0.0.1:8000/wrongbook
- OpenAPI 文档：http://127.0.0.1:8000/docs
- 环境配置指南：`docs/ENVIRONMENT.markdown`
- 技术文档：`docs/TECH_DOC.markdown`
- 演示视频：`docs/视频演示.mp4`

## 你可以用它做什么
1) **资料解析与评估闭环**
- 上传 PDF 或文本，自动生成选择题与简答题
- 判卷输出对错与解析，并记录错题
- 错题本统计关键词并给出个性化纠偏建议

2) **对话式问答**
- 直接提问，系统基于资料回答并给出证据片段

3) **可复现与云原生部署**
- Docker + Redis 编排，一键启动
- 会话与错题持久化，支持长期追踪

## 技术栈
- Python + FastAPI
- LangChain + LangGraph
- Redis
- Docker / docker-compose

## 架构速览
```
用户(浏览器)
   │  上传/问答
   ▼
前端页面 (Static)
   │  HTTP/REST
   ▼
FastAPI
   │  切分 / 检索 / 出题 / 判卷 / 问答 / 校验
   ▼
Redis (会话 / 错题 / 记录)
```

## 快速开始（推荐：Docker）
1) 准备环境变量
```powershell
Copy-Item .env.example .env
notepad .env
```
2) 启动服务
```powershell
docker compose up --build
```
3) 访问入口
- 主页：http://127.0.0.1:8000/
- 错题本：http://127.0.0.1:8000/wrongbook
- OpenAPI：http://127.0.0.1:8000/docs

## 本地运行
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LLM_API_KEY="你的_api_key"
uvicorn app.main:app --reload
```

## API 速览
- `GET /sessions`：会话列表
- `POST /sessions`：上传 PDF 并创建会话
- `POST /sessions/text`：提交文本并创建会话
- `DELETE /sessions/{session_id}`：删除会话
- `PATCH /sessions/{session_id}`：重命名会话
- `POST /questions`：生成题目
- `POST /grade`：判卷并记录错题
- `POST /chat`：基于会话资料进行问答
- `GET /wrongbook/all`：查询全局错题本
- `DELETE /wrongbook/{record_id}`：删除单条错题记录
- `GET /records/{session_id}`：获取会话最近一次题目/作答/判卷

## 最小测试流程
1. 上传 PDF，获得 `session_id`。
2. `POST /questions` 生成题目。
3. `POST /grade` 提交答案并判卷。
4. 打开错题本页面查看统计与建议。
5. 在对话入口提问并查看证据片段。

## 仓库结构
```
.
├── app/
│   ├── main.py
│   ├── models.py
│   ├── services/
│   ├── core/
│   └── static/
├── docs/
│   ├── ENVIRONMENT.markdown
│   ├── TECH_DOC.markdown
│   └── 视频演示.mp4
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 文档
- `docs/ENVIRONMENT.markdown`：依赖与环境配置指南
- `docs/TECH_DOC.markdown`：技术文档（架构、分工、智能体策略）
- `docs/视频演示.mp4`：演示视频录屏文件
