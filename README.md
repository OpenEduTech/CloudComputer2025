<h1 align="center" style="letter-spacing: 0.6px; margin-top: 4px;">
  🛡️ <span style="font-family: 'Comic Sans MS', 'Comic Neue', 'Noto Sans SC', cursive; font-weight: 800; font-size: 50px; letter-spacing: 0.1px;">PatPat-Inconsistency-Hunter</span>
</h1>
<h3 align="center" style="letter-spacing: 0.6px; margin-top: 4px;">
  <span style="font-family: 'Noto Sans SC', 'Comic Sans MS', cursive; font-weight: 500; letter-spacing: 0.6px;">长文本事实卫士-智能文档一致性检测与协作系统</span>
</h3>

---

![image-20260122112156440](assets/image-20260122112156440.png)

---

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18-blue?logo=react" alt="React" />
  <img src="https://img.shields.io/badge/TipTap-2.1-purple?logo=tiptap" alt="TipTap" />
  <img src="https://img.shields.io/badge/Docker-Ready-blue?logo=docker" alt="Docker" />
  <img src="https://img.shields.io/badge/Redis-7-red?logo=redis" alt="Redis" />
  <img src="https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql" alt="PostgreSQL" />
</p>

---

## 📖 项目简介

**PatPat-Inconsistency-Hunter** 是一个面向长文档的事实一致性检测与协作编辑平台，结合 LLM 事实抽取、冲突检测、富文本编辑与实时协作，帮助团队在论文、报告、规范等长文本中快速定位前后不一致的信息。平台支持访客模式，团队可以先用起来，再决定是否注册沉淀历史与数据。

### 🎯 适用场景

- 📄 多人协作撰写的长文档（论文、可行性报告、技术方案）
- 🔁 同一数据在不同章节反复引用的文档
- ✅ 需要事实冲突定位与报告导出的审核流程

---

### 🎯成员分工
组内统一分数

|    成员    |    学号     |     角色     |                           负责模块                           | 贡献占比 |
| :--------: | :---------: | :----------: | :----------------------------------------------------------: | :------: |
| **余超毅** | 10235501470 | 算法/Agent组 | LangGraph工作流、Prompt工程、事实提取、冲突检测、溯源验证、视觉模型集成 | **33%**  |
|  **吴彤**  | 10222140442 | 架构/工程组  |   系统架构设计、Docker部署、数据库设计、Redis集成、API开发   | **33%**  |
| **王惜冉** | 10235501401 | 前端/交互组  | React前端开发、富文本编辑器、协作功能、可视化仪表盘、UI/UX设计 | **33%**  |

## ✨ 功能概览

### 📊 文档分析与报告

|          功能          |                        描述                        |
| :--------------------: | :------------------------------------------------: |
|  🔍**事实提取**  | 基于 DeepSeek 自动抽取数值、时间、实体、结论等事实 |
|  ⚡**冲突检测**  |           对比事实并分类冲突类型与严重度           |
|  ✅**可选验证**  |           支持跳过或开启冲突二次验证流程           |
|  📈**任务进度**  |     Redis 缓存任务状态，WebSocket 实时推送进度     |
|  🧾**文档解析**  |   支持 TXT/Markdown/DOCX/PDF 解析为 TipTap JSON   |
| 🖼️**图片识别** |     InternVL3_5-4B-HF 视觉模型识别文档图片内容     |
|  📤**报告导出**  |      分析报告导出 Markdown/JSON/PDF/DOCX/TXT      |
|   🔒**检测锁**   |       Redis 分布式锁 + 内容哈希防止重复分析       |

![03f0011fefffd10589e0bec8a01ce8a6](assets/03f0011fefffd10589e0bec8a01ce8a6.png)

#### 🔍 冲突类型说明

系统支持检测以下八种类型的冲突：

|        冲突类型        | 描述                                 | 示例                                                                   |
| :--------------------: | :----------------------------------- | :--------------------------------------------------------------------- |
|  **数值冲突**🔢  | 同一概念在不同位置出现不同的数值     | "项目预算为 100 万元" vs "项目预算为 150 万元"                         |
|  **时间冲突**⏰  | 同一事件在不同位置出现不同的时间描述 | "会议于 2024 年 1 月举行" vs "会议于 2024 年 2 月举行"                 |
|  **实体冲突**👤  | 同一概念指向不同的实体或人物         | "项目负责人是张三" vs "项目负责人是李四"                               |
|  **类别冲突**📂  | 同一概念被归入不同的分类体系         | "机器学习分为监督学习和无监督学习" vs "机器学习分为深度学习和强化学习" |
|  **定义冲突**📖  | 同一术语在不同位置有不同的定义       | "AI 是模拟人类智能的技术" vs "AI 是自动化决策系统"                     |
|  **逻辑冲突**🧩  | 陈述之间存在逻辑矛盾                 | "所有用户都已登录" vs "部分用户未登录"                                 |
|  **空间冲突**📍  | 同一对象在不同位置出现不同的空间描述 | "办公室位于 3 楼" vs "办公室位于 5 楼"                                 |
| **图文冲突**🖼️ | 文本描述与图片内容不一致             | 文本描述"销售额增长 20%" vs 图表显示"销售额下降 10%"                   |

### 👥 协作编辑

|          功能          |                    描述                    |
| :--------------------: | :----------------------------------------: |
|  🏠**房间管理**  |    创建、加入、结束协作房间，支持邀请码    |
|  🔄**实时同步**  |     WebSocket 协同编辑与协作者光标显示     |
| 🔐**分章节锁定** |         房主分配章节、锁定编辑权限         |
| 🧭**检测与推送** |   触发检测、查看状态、取消检测、推送结果   |
|  📤**房间导出**  | 支持 md/html/txt/docx/pdf 导出，含可选分析 |
|  👥**成员管理**  |           踢出成员、调整房间设置           |

![0dc443f9d96537cc0c6358ff5a463ef2](assets/0dc443f9d96537cc0c6358ff5a463ef2.png)

### 🎨 文档与内容管理

|          功能          |                   描述                   |
| :--------------------: | :---------------------------------------: |
| 📝**富文本编辑** | TipTap 编辑器，支持字体、颜色、对齐、表格 |
| 🖼️**图片上传** |      文档/房间图片上传与静态资源管理      |
| 📚**个人文档库** |      文档 CRUD、版本、状态与字数统计      |
|  📦**文档导出**  |    文档导出 markdown/html/pdf/docx/txt    |

![a768873410e56e204adef69c8e2424e7](assets/a768873410e56e204adef69c8e2424e7.png)

### 👤 用户与统计

|          功能          |            描述            |
| :--------------------: | :------------------------: |
|  🔐**JWT 认证**  | 注册/登录/登出/Token 校验 |
|  👤**个人资料**  | 头像上传、显示名、邮箱修改 |
| 📊**统计仪表盘** |    总览 + 详细统计图表    |
|  🧾**分析历史**  |   任务分析历史与结果回溯   |

![b87082e8a1baf0d37d2880d20d822380](assets/b87082e8a1baf0d37d2880d20d822380.png)

![7944e8cd98073bc74ed7c988c22fa3f4](assets/7944e8cd98073bc74ed7c988c22fa3f4.png)

![24395d0bc0bdd363230b21242935775e](assets/24395d0bc0bdd363230b21242935775e.png)

---

## ✅ 已实现功能

### 文档分析

- [X] 文档检测锁（内容哈希 + Redis 分布式锁）
- [X] 文档解析：TXT/Markdown/DOCX/PDF → TipTap JSON，支持图片提取/网络图片下载
- [X] 图像识别：InternVL3_5-4B-HF 视觉模型识别图片内容
- [X] 文档分块、事实提取、冲突检测、冲突验证（可跳过）
- [X] 任务状态/进度/结果/原文/事实黑板/冲突黑板缓存由 Redis 承载，WebSocket 推送
- [X] 结果与列表接口：摘要/事实/冲突/原文
- [X] 任务文档编辑与重新分析
- [X] 报告导出：markdown/json/pdf/docx/txt
- [X] 原文导出：txt/md/pdf/docx

### 协作编辑

- [X] 房间创建/加入/列表/详情/结束，支持邀请码与描述
- [X] 协作模式：实时协同 / 分章节锁定
- [X] 房主设置：房间名、文档标题、最大成员数
- [X] 章节权限分配/取消、章节增删、章节锁获取与释放
- [X] WebSocket 实时同步：内容更新、协作者光标
- [X] 房间检测：触发/状态查询/取消/冲突列表
- [X] 房间状态/成员在线/章节锁/检测结果缓存统一由 Redis 承载
- [X] 房间导出：md/html/txt/docx/pdf（可选包含分析结果）
- [X] 成员管理：踢出成员
- [X] 编辑历史与房间内容持久化
- [X] 支持游客加入协作房间（未登录）

### 文档与资源

- [X] 用户文档库 CRUD、版本与字数统计
- [X] 富文本内容转换：JSON/HTML/纯文本
- [X] 文档导出：markdown/html/pdf/docx/txt
- [X] 文档/协作图片上传与管理
- [X] 编辑草稿/图片下载/解析临时缓存统一由 Redis 管理
- [X] 用户头像上传

### 用户与统计

- [X] 注册/登录/登出/Token 校验
- [X] 个人资料更新、修改密码
- [X] 统计概览/详细图表与仪表盘数据
- [X] 分析历史与用户协作统计

### 运维与部署

- [X] Docker Compose 一键部署（前端/后端/Redis/PostgreSQL）
- [X] Nginx 反向代理与 WebSocket 支持
- [X] 健康检查接口与日志目录
- [X] 大文件上传配置（默认 100MB）

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                            用户界面                                    │
│              (React 18 + TailwindCSS + TipTap + Framer Motion)        │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      API 网关 + WebSocket                              │
│                      (Nginx + FastAPI)                                │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
    ┌──────────────────┬──────────┼──────────┬───────────────────┐
    ▼                  ▼          ▼          ▼                   ▼
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
│ 事实提取器  │  │ 冲突检测器  │  │ 协作服务    │  │ 文档编辑器  │  │ 用户认证    │
│ Fact       │  │ Conflict   │  │ Room Mgr   │  │ Document   │  │ Auth       │
│ Extractor  │  │ Detector   │  │ WebSocket  │  │ Editor     │  │ Service    │
└────────────┘  └────────────┘  │ ChapterLock│  │ Service    │  └────────────┘
      │              │          └────────────┘  └────────────┘         │
      │              │                │               │                │
      └──────────────┴────────────────┴───────────────┴────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│          DeepSeek LLM API + InternVL3_5-4B-HF Vision Model            │
└──────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
┌───────────────────────────────┐         ┌───────────────────────────────┐
│    Redis (实时状态与缓存)       │         │   PostgreSQL (持久化存储)       │
│ • 任务状态/进度缓存             │         │ • 用户数据                      │
│ • 房间实时状态/成员             │         │ • 文档与分析结果                │
│ • 章节锁定/检测锁               │         │ • 协作房间与成员                │
│ • WebSocket 会话/游标           │         │ • 编辑历史记录                  │
└───────────────────────────────┘         │ • 富文本内容与图片              │
                                          └───────────────────────────────┘
```

系统核心分析链路由 **LangGraph 后端算法**编排，统一负责任务状态流转、节点编排与失败回退，保证复杂文档分析的可控与可追踪。

### 🔧 技术栈

**后端 (Python 3.12):**

- FastAPI - 现代异步 Web 框架
- SQLAlchemy 2.0 - 异步 ORM
- DeepSeek API - 大语言模型
- InternVL3_5-4B-HF - 视觉模型（图片内容识别）
- Redis - 实时状态管理
- PostgreSQL 15 - 数据持久化
- WebSocket - 实时通信
- python-jose + passlib/bcrypt - 用户认证
- PyMuPDF/pdfplumber - PDF 解析
- python-docx/markdown/bleach - 文档解析
- WeasyPrint/ReportLab - 文档导出
- Pillow - 图片处理

**前端 (React 18):**

- Vite - 构建工具
- TailwindCSS - 样式框架
- TipTap 2.1 - 富文本编辑器
- Framer Motion - 动画库
- Recharts - 数据可视化
- Lucide React - 图标库
- axios - API 请求
- JSZip/docx/html2pdf - 文档导出
- file-saver/pdfjs - 文件下载与预览

**部署:**

- Docker + Docker Compose
- Nginx - 反向代理

---

## 🧠 后端算法（LangGraph）

LangGraph 构建多模态一致性检测的**分析图谱**，将解析、视觉理解、事实抽取与冲突推理编排为可观测、可回滚的状态机/DAG 流水线：

```
┌───────────────────────────────────────────────────────────────────┐
│                        LangGraph 分析图                            │
├───────────────────────────────────────────────────────────────────┤
│  输入文档/富文本                                                    │
│         │                                                         │
│         ▼                                                         │
│  解析与结构化 → 图片提取 → 视觉理解(InternVL3_5-4B-HF)             │
│         │                                                         │
│         ▼                                                         │
│  事实抽取(DeepSeek) → 事实过滤 → 冲突检测                         │
│         │                                                         │
│         ▼                                                         │
│  溯源验证(可选) → 结果汇总 → 持久化(PostgreSQL)                   │
│         │                                                         │
│         ▼                                                         │
│  状态/进度/锁 → Redis                                              │
└───────────────────────────────────────────────────────────────────┘
```

1. **多模态结构化**：解析文档为 TipTap JSON，抽取文本与图片引用。
2. **视觉语义注入**：InternVL3_5-4B-HF 生成图片描述并回填占位符。
3. **事实抽取层**：DeepSeek 抽取结构化事实与数值实体。
4. **事实净化层**：过滤低置信度或无需核验的事实。
5. **一致性推理**：冲突检测与严重度分级。支持检测八种冲突类型：🔢 数值冲突、⏰ 时间冲突、👤 实体冲突、📂 类别冲突、📖 定义冲突、🧩 逻辑冲突、📍 空间冲突、🖼️ 图文冲突。
6. **证据回溯（可选）**：对冲突进行二次验证与建议生成。
7. **结果汇总**：生成报告与指标摘要，持久化到 PostgreSQL。

算法特性：

- **图谱化编排**：节点级编排与依赖关系清晰可控。
- **状态可回溯**：失败可重试或回退到指定节点。
- **阶段可观测**：进度与阶段状态统一写入 Redis。
- **可扩展节点**：支持按需插入新的分析节点（如规则校验、质量评分）。

## 🚀 快速开始

### 前置要求

- Docker 和 Docker Compose
- DeepSeek API 密钥

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/PatPat-Inconsistency-Hunter.git
cd PatPat-Inconsistency-Hunter
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp env.example.txt .env

# 编辑 .env 文件，填入必要配置
```

**关键环境变量：**

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 数据库配置
DATABASE_URL=postgresql://patpat:patpat123@postgres:5432/patpat_db

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379

# 安全配置
SECRET_KEY=your_jwt_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

### 3. 下载模型（本地）

请将 **InternVL3_5-4B-HF** 视觉模型下载到本地 `models/InternVL3_5-4B-HF` 目录下，确保后端可直接加载该模型。

### 4. 启动服务

```bash
# 使用 Docker Compose 一键启动
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 5. 访问应用

|   服务   |               地址               |     描述     |
| :------: | :------------------------------: | :----------: |
| 前端界面 |      http://localhost:3000      | Web 应用入口 |
| API 文档 |    http://localhost:8000/docs    |  Swagger UI  |
| 健康检查 | http://localhost:8000/api/health |   服务状态   |

---

## 📁 项目结构

```
PatPat-Inconsistency-Hunter/
├── .env                              # 本地环境变量
├── server/                          # 后端服务
│   ├── app/
│   │   ├── api/                     # API 路由
│   │   │   ├── routes.py            # 分析/任务/统计路由
│   │   │   ├── auth_routes.py       # 用户认证路由
│   │   │   ├── collaboration_routes.py # 协作路由
│   │   │   └── document_routes.py   # 文档内容管理路由
│   │   ├── models/                  # 数据模型
│   │   │   ├── schemas.py           # Pydantic 模型
│   │   │   └── database.py          # SQLAlchemy ORM 模型
│   │   ├── services/                # 核心业务逻辑
│   │   │   ├── llm_client.py        # DeepSeek 客户端
│   │   │   ├── fact_extractor.py    # 事实提取器
│   │   │   ├── conflict_detector.py # 冲突检测器
│   │   │   ├── fact_verifier.py     # 事实验证器
│   │   │   ├── document_processor.py # 文档处理器
│   │   │   ├── analysis_engine.py   # 分析引擎
│   │   │   ├── document_editor.py   # 文档编辑服务
│   │   │   ├── auth.py              # 用户认证服务
│   │   │   ├── prompts.py           # Prompt 模板
│   │   │   └── collaboration/       # 协作服务
│   │   │       ├── room_manager.py      # 房间管理
│   │   │       ├── chapter_lock.py      # 章节锁定
│   │   │       ├── websocket_manager.py # WebSocket 管理
│   │   │       ├── realtime_detector.py # 实时冲突检测
│   │   │       └── room_persistence.py  # 房间数据持久化
│   │   ├── utils/                   # 工具函数
│   │   │   ├── db_session.py        # 数据库会话管理
│   │   │   ├── redis_client.py      # Redis 客户端
│   │   │   ├── logger.py            # 日志配置
│   │   │   └── async_utils.py       # 异步工具
│   │   ├── config.py                # 配置文件
│   │   └── main.py                  # FastAPI 入口
│   ├── requirements.txt             # Python 依赖
│   ├── Dockerfile                   # 后端 Docker 配置
│   └── init.sql                     # 数据库初始化脚本
│
├── client/                          # 前端应用
│   ├── public/                      # 静态资源
│   ├── src/
│   │   ├── api/                     # API 客户端
│   │   │   ├── index.js             # 文档分析 API
│   │   │   └── collaboration.js     # 协作 API
│   │   ├── components/              # React 组件
│   │   │   ├── RichTextEditor.jsx   # 富文本编辑器
│   │   │   ├── CollaboratorCursor.jsx # 协作者光标
│   │   │   ├── AnalysisSidebar.jsx  # 分析侧边栏
│   │   │   ├── OwnerPanel.jsx       # 房主管理面板
│   │   │   └── ...
│   │   ├── pages/                   # 页面组件
│   │   │   ├── HomePage.jsx         # 首页
│   │   │   ├── AnalyzePage.jsx      # 文档分析页
│   │   │   ├── ResultPage.jsx       # 分析结果页
│   │   │   ├── DashboardPage.jsx    # 仪表盘
│   │   │   ├── CollaboratePage.jsx  # 协作空间入口
│   │   │   ├── CollaborateRoomPage.jsx # 协作房间
│   │   │   ├── JoinRoomPage.jsx     # 加入房间
│   │   │   ├── ProfilePage.jsx      # 个人中心
│   │   │   ├── LoginPage.jsx        # 登录页
│   │   │   └── RegisterPage.jsx     # 注册页
│   │   ├── contexts/
│   │   │   └── AuthContext.jsx      # 认证状态管理
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── Dockerfile                   # 前端 Docker 配置
│   └── nginx.conf                   # Nginx 配置
│
├── docker-compose.yml               # Docker Compose 配置
├── .gitignore
├── env.example.txt                  # 环境变量示例
├── logs/                            # 后端日志
├── models/                          # 本地模型目录
│   └── InternVL3_5-4B-HF/           # 视觉模型权重（需本地下载）
├── uploads/                         # 图片/头像上传目录
└── README.md
```

---

## 📊 数据库设计

### PostgreSQL 表结构

|           表名           |     描述     |               主要字段               |
| :----------------------: | :----------: | :-----------------------------------: |
|        `users`        |    用户表    | user_id, username, email, avatar_url |
|      `documents`      | 分析任务文档 |    task_id, title, content, status    |
|        `facts`        |   事实记录   |    fact_id, fact_type, source_text    |
|      `conflicts`      |   冲突记录   | conflict_id, conflict_type, severity |
|   `analysis_history`   | 分析过程记录 |    task_id, step_name, step_status    |
|    `user_documents`    | 用户个人文档 |  document_id, title, status, version  |
|   `document_images`   | 文档图片资源 |      image_id, file_url, room_id      |
| `collaboration_rooms` |   协作房间   | room_id, room_name, mode, invite_code |
|   `room_memberships`   |   房间成员   |        room_id, user_id, role        |
|    `edit_histories`    |   编辑历史   |    room_id, action, content_before    |
| `chapter_lock_records` |  章节锁记录  |    room_id, chapter_id, expires_at    |
|   `detection_locks`   |    检测锁    |   target_type, target_id, locked_by   |

### Redis 数据结构

所有实时状态与缓存统一由 Redis 实现（无论实际运行位置），覆盖：

- 任务状态/进度/结果/原文缓存
- 事实黑板与冲突黑板（分析中间态）
- 文档编辑草稿与协作房间内容
- 房间状态/成员在线/用户房间映射
- 章节锁/检测锁/检测结果/最近检测时间
- 图片下载/解析临时缓存
- 前端会话与任务列表本地缓存（统一以 Redis 为后端来源）
- 静态资源缓存策略元信息（与 Nginx/浏览器协同）

|               Key 模式               |       描述       |
| :----------------------------------: | :---------------: |
|      `task:{task_id}:status`      |     任务状态     |
|     `task:{task_id}:progress`     |     任务进度     |
|      `task:{task_id}:result`      |   任务结果缓存   |
|     `task:{task_id}:document`     |   文档原文缓存   |
|     `fact:{task_id}:{fact_id}`     |   事实黑板缓存   |
| `conflict:{task_id}:{conflict_id}` |   冲突黑板缓存   |
|  `document:{document_id}:editing`  |   编辑草稿缓存   |
|       `room:{room_id}:state`       |   房间实时状态   |
|      `room:{room_id}:members`      |   在线成员列表   |
|     `room:{room_id}:detection`     |   检测结果缓存   |
|       `room:{room_id}:locks`       |  章节/检测锁状态  |
|       `user:{user_id}:room`       |   用户当前房间   |
|      `image:{image_id}:temp`      | 图片下载/解析缓存 |

---

## 📡 API 接口

### 文档分析接口

|  方法  |                  路径                  |        描述        |
| :----: | :-------------------------------------: | :----------------: |
|  POST  |            `/api/analyze`            |  提交文档分析任务  |
|  GET  |     `/api/task/{task_id}/status`     |    获取任务状态    |
|  GET  |     `/api/task/{task_id}/result`     |    获取分析结果    |
|  GET  |      `/api/task/{task_id}/facts`      |    获取事实列表    |
|  GET  |    `/api/task/{task_id}/conflicts`    |    获取冲突列表    |
|  GET  |    `/api/task/{task_id}/document`    | 获取原文（含分块） |
|  PUT  |    `/api/task/{task_id}/document`    |  更新任务文档内容  |
|  POST  |    `/api/task/{task_id}/reanalyze`    |    重新分析文档    |
|  GET  |     `/api/task/{task_id}/export`     |    导出分析报告    |
|  GET  | `/api/task/{task_id}/document/export` |    导出任务文档    |
| DELETE |         `/api/task/{task_id}`         |      删除任务      |
|  POST  |         `/api/parse-document`         |    解析上传文件    |
|  GET  |             `/api/health`             |      健康检查      |
|  GET  |         `/api/stats/overview`         |      统计概览      |
|  GET  |         `/api/stats/detailed`         |      详细统计      |
|  GET  |      `/api/user/dashboard-stats`      |   用户仪表盘统计   |
|  GET  |     `/api/user/analysis-history`     |    用户分析历史    |

### 用户认证接口

| 方法 |             路径             |         描述         |
| :--: | :---------------------------: | :------------------: |
| POST |    `/api/auth/register`    |       用户注册       |
| POST |      `/api/auth/login`      |       用户登录       |
| GET |       `/api/auth/me`       |   获取当前用户信息   |
| PUT |       `/api/auth/me`       |     更新用户信息     |
| POST |     `/api/auth/avatar`     |     上传用户头像     |
| POST | `/api/auth/change-password` |       修改密码       |
| POST |     `/api/auth/logout`     |       用户登出       |
| GET |      `/api/auth/check`      |     检查登录状态     |
| PUT |     `/api/auth/profile`     | 更新用户资料（别名） |

### 协作接口

|  方法  |                             路径                             |        描述        |
| :----: | :----------------------------------------------------------: | :----------------: |
|  POST  |                 `/api/collaboration/rooms`                 |    创建协作房间    |
|  GET  |                 `/api/collaboration/rooms`                 |    获取房间列表    |
|  GET  |            `/api/collaboration/rooms/{room_id}`            |    获取房间详情    |
|  POST  |         `/api/collaboration/rooms/{room_id}/join`         |      加入房间      |
|  POST  |         `/api/collaboration/rooms/{room_id}/leave`         |      离开房间      |
|  POST  |          `/api/collaboration/rooms/{room_id}/end`          |      结束房间      |
|  GET  |        `/api/collaboration/rooms/{room_id}/export`        |    导出房间文档    |
|  POST  |         `/api/collaboration/rooms/{room_id}/kick`         |      踢出成员      |
|  PUT  |        `/api/collaboration/rooms/{room_id}/content`        |    更新文档内容    |
|  PUT  | `/api/collaboration/rooms/{room_id}/chapters/{chapter_id}` |    更新章节内容    |
|  POST  |         `/api/collaboration/rooms/{room_id}/locks`         |     获取章节锁     |
| DELETE |  `/api/collaboration/rooms/{room_id}/locks/{chapter_id}`  |     释放章节锁     |
|  GET  |         `/api/collaboration/rooms/{room_id}/locks`         |     获取房间锁     |
|  PUT  |       `/api/collaboration/rooms/{room_id}/settings`       |    更新房间设置    |
|  POST  |    `/api/collaboration/rooms/{room_id}/assign-chapter`    |    分配章节权限    |
|  POST  |   `/api/collaboration/rooms/{room_id}/unassign-chapter`   |    取消章节权限    |
|  POST  |       `/api/collaboration/rooms/{room_id}/chapters`       |      添加章节      |
| DELETE | `/api/collaboration/rooms/{room_id}/chapters/{chapter_id}` |      删除章节      |
|  GET  |        `/api/collaboration/rooms/{room_id}/members`        |    获取成员列表    |
|  POST  |        `/api/collaboration/rooms/{room_id}/detect`        |    触发冲突检测    |
|  GET  |   `/api/collaboration/rooms/{room_id}/detection/status`   |      检测状态      |
|  POST  |   `/api/collaboration/rooms/{room_id}/detection/cancel`   |      取消检测      |
|  GET  |       `/api/collaboration/rooms/{room_id}/conflicts`       |    获取房间冲突    |
|  GET  |            `/api/collaboration/user/documents`            |  获取用户文档列表  |
|   WS   |   `/api/collaboration/ws/{room_id}/{user_id}/{username}`   | WebSocket 实时通信 |

### 文档内容管理接口

|  方法  |                  路径                  |     描述     |
| :----: | :-------------------------------------: | :----------: |
|  GET  |           `/api/documents`           | 获取文档列表 |
|  POST  |           `/api/documents`           |   创建文档   |
|  GET  |    `/api/documents/{document_id}`    | 获取文档详情 |
|  PUT  |    `/api/documents/{document_id}`    |   更新文档   |
| DELETE |    `/api/documents/{document_id}`    |   删除文档   |
|  POST  |    `/api/documents/images/upload`    | 上传文档图片 |
|  GET  | `/api/documents/{document_id}/export` |   导出文档   |
|  GET  |   `/api/documents/analysis/history`   |   分析历史   |
|  GET  |    `/api/documents/stats/overview`    | 用户统计概览 |

---

## 🔄 工作流程

### 单文档分析流程

```
1. 用户上传/输入文档
       │
       ▼
2. 文档解析（TXT/Markdown/DOCX/PDF → TipTap JSON）
       │
       ▼
3. 图片提取（解析 PDF/DOCX 中的图片并落库）
       │
       ▼
4. 图片识别（InternVL3_5-4B-HF 生成图片描述并替换占位符）
       │
       ▼
5. 生成可分析的纯文本（合并文本 + 图片描述）
       │
       ▼
6. 文档级锁定（同一文档不可重复提交）
       │
       ▼
7. 文档预处理（分块、结构分析）
       │
       ▼
8. 事实提取（调用 DeepSeek）
       │
       ▼
9. 事实过滤（去除不需要检验的事实）
       │
       ▼
10. 冲突检测（两两比对或批量检测）
       │
       ▼
11. 溯源验证（分析冲突，给出建议，可跳过）
       │
       ▼
12. 结果持久化（保存到 PostgreSQL）
       │
       ▼
13. 生成报告（可视化展示、多格式导出）
```

### 多人协作流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                           协作空间                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   房主创建房间                                                        │
│   ├── 设置邀请码                                                     │
│   ├── 选择协作模式（实时协同 / 分章节锁定）                              │
│   └── 选择初始文档（新建 / 已有文档）                                   │
│                                                                     │
│   ┌───────────────────────┐       ┌───────────────────────┐         │
│   │    实时协同模式         │       │   分章节锁定模式        │         │
│   └───────────┬───────────┘       └───────────┬───────────┘         │
│               │                               │                     │
│               ▼                               ▼                     │
│   ┌───────────────────────┐       ┌───────────────────────┐         │
│   │ • 多人同时编辑          │       │ • 房主分配章节权限       │         │
│   │ • 实时同步内容          │       │ • 每人编辑自己的章节     │         │
│   │ • 协作者光标位置共享    │       │ • 章节锁定防止冲突       │         │
│   │ • 富文本编辑支持        │       │ • 房主可编辑所有章节     │         │
│   └───────────┬───────────┘       └───────────┬───────────┘         │
│               │                               │                     │
│               └───────────────┬───────────────┘                     │
│                               │                                     │
│                               ▼                                     │
│               ┌───────────────────────────────┐                     │
│               │      实时冲突检测服务           │                     │
│               │  (点击"保存"或"检测冲突"触发)   │                     │
│               │  (检测期间全局锁定)             │                     │
│               └───────────────┬───────────────┘                     │
│                               │                                     │
│                               ▼                                     │
│               ┌───────────────────────────────┐                     │
│               │    WebSocket 推送检测结果       │                     │
│               │ • 实时协同：所有人收到全部冲突   │                     │
│               │ • 章节锁定：各人收到自己章节冲突  │                     │
│               │ • 房主收到所有冲突              │                     │
│               └───────────────────────────────┘                     │
│                                                                     │
│   房间管理功能                                                        │
│   ├── 邀请码管理                                                     │
│   ├── 成员管理（踢人）                                                │
│   ├── 结束房间                                                       │
│   └── 导出文档（支持 Markdown/HTML/PDF）                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 统计与个人中心流程

```
1. 分析任务完成并写入 PostgreSQL
       │
       ▼
2. 系统统计聚合（/stats/overview, /stats/detailed）
       │
       ▼
3. 仪表盘展示（Dashboard）
       │   • 任务总量/完成数/事实总量/冲突总量
       │   • 冲突类型分布/严重度分布/周趋势图
       │   • 个人统计卡片（登录态：累计文档/完成率/事实/冲突）
       ▼
4. 用户维度统计（/user/dashboard-stats）
       │   • 我的文档、完成率、协作房间、最近活动
       │   • 参与房间统计（创建/加入/协作次数）
       ▼
5. 个人中心历史（/user/analysis-history）
           • 分析记录列表 + 累计统计（总分析数/完成数/事实/冲突）
           • 快速跳转结果页与删除记录
```

---

## 🐳 Docker 部署

### 服务组件

|   服务   | 端口 |                   描述                   |
| :------: | :--: | :--------------------------------------: |
|  client  | 3000 |              前端 Web 界面              |
|  server  | 8000 |              后端 API 服务              |
|  redis  | 6379 |            统一缓存与状态中心            |
| postgres | 5433 | 数据持久化（映射到宿主机 5433 避免冲突） |

### 常用命令

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重新构建并启动
docker compose up -d --build

# 查看日志
docker compose logs -f server
docker compose logs -f client

# 进入容器
docker compose exec server bash
docker compose exec postgres psql -U patpat -d patpat_db

# 清理数据（包括数据库）
docker compose down -v
```

---

## 🎨 智能体设计

系统通过 Prompt 模板驱动事实抽取、冲突检测，并在检测环节加入事实过滤、相关性预筛选、置信度评估与可选二次验证，以降低模型幻觉影响。

---

## 📝 许可证

本项目仅供学习和教育目的使用。

---

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供大语言模型 API
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [React](https://react.dev/) - 前端 UI 框架
- [TipTap](https://tiptap.dev/) - 富文本编辑器
- [TailwindCSS](https://tailwindcss.com/) - CSS 框架
- [Recharts](https://recharts.org/) - 数据可视化

---

<p align="center">
  <sub>Built with ❤️ by PatPat Team | © 2026</sub>
</p>
