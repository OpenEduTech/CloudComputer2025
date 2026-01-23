# Cloud_Final
This is the repository of our final project of Cloud Computing System.

## 项目backend结构

```
backend/app/
├── main.py                    # FastAPI 应用入口：创建 app、注册所有 router、定义健康检查等全局配置
├── api/                       # HTTP 边界层：负责接收请求、参数校验、创建业务实体、投递异步任务
│   ├── materials.py            # 学习资料管理 API：上传/登记学习材料，触发教材解析与知识抽取流程
│   ├── quizzes.py              # 测验管理 API：创建测验任务，触发出题流程，查询测验基本信息
│   ├── attempts.py             # 作答与判卷 API：提交学生答案，触发自动判卷任务，查询判卷结果
│   ├── mistakes.py             # 错题本 API：查询学生历史错误、薄弱知识点与错题统计信息
│   ├── knowledge.py            # 知识体系树 API：读取章节/小节/知识点与掌握度
│   ├── coach.py                # 小灶建议 API：生成学习诊断与纠偏计划
│   └── tutor.py                # 引导式教学 API：启动并维护 Tutor 对话会话（多轮引导、非直接给答案）
│
├── models/                    # 数据合同层：定义系统中所有核心业务实体的数据结构（Pydantic / Mongo Schema）
│   ├── material.py             # 学习资料模型：表示教材/文本等输入原材料及其解析状态
│   ├── material_text.py        # 文本切片模型：全文/摘要 chunk 的持久化
│   ├── notebook.py             # Notebook 模型：主题/学科级别的隔离
│   ├── quiz.py                 # 测验模型：表示一次测验任务的元数据、状态与关联题目
│   ├── question.py             # 题目模型：表示单道题的题干、答案、难度及关联知识点
│   ├── attempt.py              # 作答模型：表示学生一次提交的答案及其判卷状态与得分
│   ├── mistake.py              # 错题模型：表示学生在某题或某知识点上的错误记录与累计次数
│   ├── knowledge_node.py       # 知识节点模型：章/节/知识点结构与来源 chunk
│   └── mastery.py              # 掌握度模型：表示学生对某个知识点的长期掌握情况与能力评分
│
├── agents/                    # LLM 智能体层：封装所有与大模型交互的推理逻辑（不直接操作数据库）
│   ├── quiz_generator.py       # 出题智能体：根据教材或知识点生成结构化测验题目
│   ├── grader.py               # 判卷智能体：根据标准答案与评分规则对学生作答进行自动评估
│   ├── coach.py                # 学习教练智能体：基于错题与掌握度生成诊断结论与学习改进建议
│   └── tutor.py                # 引导式教学智能体：通过多轮提问与提示引导学生自主纠错与理解
│
├── checkers/                  # Check Layer：对 LLM 输出进行规则校验，降低幻觉与不合规输出风险
│   ├── quiz_check.py           # 出题校验器：检查题目结构完整性、答案存在性与覆盖合理性
│   ├── grade_check.py          # 判卷校验器：检查评分结果是否有依据、格式是否符合预期
│   ├── coach_check.py          # 教练校验器：检查学习建议是否基于真实错因与掌握度数据
│   └── tutor_check.py          # Tutor 校验器：确保引导过程遵循提示层级，避免直接泄露答案
│
├── services/                  # 业务服务层：承载确定性、可复现的业务规则与数据更新逻辑（不使用 LLM）
│   ├── material_service.py     # 材料服务：材料入库与文本切片写入
│   ├── quiz_service.py         # 测验服务：测验状态管理与题目聚合
│   ├── attempt_service.py      # 作答服务：判卷状态与评分结果落库
│   ├── mastery_service.py      # 掌握度服务：根据作答结果更新学生知识点掌握度与能力评分
│   ├── mistake_service.py      # 错题服务：维护错题本数据，累计错误次数并标注薄弱知识点
│   ├── knowledge_service.py    # 知识树服务：构建章/节/知识点结构
│   ├── coach_service.py        # 小灶建议服务：生成诊断与训练计划
│   └── tutor_service.py        # Tutor 会话服务：对话状态机与记录
│
├── jobs/
│   └── queue.py                # 异步任务队列封装：统一管理 Redis/RQ 队列实例，解耦业务与队列实现
│
├── tutor_runtime/             # Tutor 运行时：提示阶梯状态机 + 输出校验
│   ├── engine.py               # Tutor 推理引擎
│   ├── tutor_check.py          # Tutor 输出校验（Hint ladder）
│   ├── gate.py                 # 失败重试与校验门控
│   ├── utils.py                # JSON/文本安全工具
│   └── base.py                 # 校验器基类
│
└── db/                        # 基础设施层：提供数据库与缓存的底层连接
    ├── mongo.py                # MongoDB 连接与数据库实例初始化
    └── redis.py                # Redis 原始连接封装（供队列与缓存等组件使用）
```

## 项目worker结构

```
worker/
├── worker.py                  # Worker 进程入口：启动队列监听，持续消费并执行后台异步任务
└── tasks/
    ├── ingest.py               # 教材解析任务：将学习资料拆分、结构化并生成知识体系（慢任务）
    ├── generate_quiz.py        # 出题任务：调用出题智能体并通过校验后写入题目数据
    ├── grade_attempt.py        # 判卷任务：调用判卷智能体、校验评分结果并更新作答与错题记录
    ├── coach.py                # 学习教练任务：生成针对学生薄弱点的个性化学习建议
    └── tutor.py                # Tutor 对话任务：执行引导式教学对话逻辑并维护会话状态
```

## 环境配置与启动

### Docker Compose（推荐）
1. 在仓库根目录创建 `.env`（不要提交）：
```
MOONSHOT_API_KEY=你的_key
GROQ_API_KEY=你的_key
ZHIPU_API_KEY=你的_key
KIMI_MODEL=moonshot-v1-8k
VITE_API_BASE_URL=http://localhost:8000
```
2. 启动：
```
docker compose up -d --build
```
3. 访问：
- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

### 本地开发（不走 Docker）
1. 启动本地 MongoDB / Redis
2. 设置环境变量（PowerShell 示例）：
```
$env:MONGO_URI="mongodb://localhost:27017/mydb"
$env:REDIS_URL="redis://localhost:6379"
$env:MOONSHOT_API_KEY="你的_key"
$env:GROQ_API_KEY="你的_key"
$env:ZHIPU_API_KEY="你的_key"
$env:VITE_API_BASE_URL="http://localhost:8000"
```
3. 启动后端与 worker：
```
cd backend
python -m uvicorn app.main:app --reload --port 8000

cd ../worker
python worker.py
```
4. 启动前端：
```
cd ../frontend
npm install
npm run dev
```

### 关键环境变量（建议写在根目录 `.env`）
| 变量 | 必需 | 说明 |
| --- | --- | --- |
| `MOONSHOT_API_KEY` | ✅ | Kimi：PDF/DOCX 抽取、出题、判卷、知识树、Tutor |
| `GROQ_API_KEY` | ⛳️（音频需要） | Groq：ASR 语音转写 |
| `ZHIPU_API_KEY` | ⛳️（RAG 需要） | Embedding API：向量化 |
| `KIMI_MODEL` | 可选 | 默认 `moonshot-v1-8k` |
| `MONGO_URI` | 本地运行需要 | 默认 `mongodb://localhost:27017/mydb` |
| `REDIS_URL` | 本地运行需要 | 默认 `redis://localhost:6379` |
| `VITE_API_BASE_URL` | 前端可选 | 默认 `http://localhost:8000` |
| `UPLOAD_DIR` | 可选 | 默认 `storage/uploads`（上传文件路径） |
