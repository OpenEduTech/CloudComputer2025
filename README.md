# ConceptGraph AI - 跨学科知识图谱系统

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![React](https://img.shields.io/badge/React-18+-61DAFB.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

> **交付说明**: 本项目已包含完整的Dockerfile、依赖配置文件、源码及部署指南，详见下文和ENVIRONMENT_SETUP.md

**讲解视频支持两种查看方式：**（1）百度网盘：通过网盘分享的文件：云计算期末项目介绍视频_张凯诚&肖璟仪.mp4
链接: https://pan.baidu.com/s/1X6FCAfteKOZoLAdPBkA7tA?pwd=u8pt 提取码: u8pt

(2)bilibili: https://www.bilibili.com/video/BV1EnBfBtEme/?spm_id_from=333.1387.upload.video_card.click&vd_source=a90c2203ec4b3b9d67ddad0d9e7bc495

## 项目简介

**ConceptGraph AI** 是一个基于大语言模型（LLM）和图数据库的跨学科知识图谱系统。通过多源数据融合（LLM + Wikipedia + Arxiv + OpenAI Embedding）和三层缓存架构（Neo4j + Redis + LLM）实现高性能概念关联发现、语义筛选和可视化。

### 核心功能

1. **功能1 - 自动跨学科挖掘**: 输入单个概念，自动发现跨学科关联概念
2. **功能2 - 指定学科挖掘**: 在指定学科范围内挖掘相关概念
3. **功能3 - 桥接概念发现**: 找到连接多个概念的"桥梁节点"

### 技术特点

- **三层缓存架构**: Neo4j（持久化） → Redis（1小时TTL） → LLM（实时生成）
- **多源数据融合**: LLM生成 + Wikipedia权威验证 + Arxiv学术支持
- **语义相似度筛选**: OpenAI Embedding API计算768维向量，过滤相关度 > 0.6的节点
- **异步并发处理**: AsyncIO并行调用多个API，提升响应速度
- **完整图可视化**: D3.js力导向图 + Ant Design交互界面
- **Docker一键部署**: docker-compose编排4个容器

---

## 快速开始

### 方式一：Docker一键部署（推荐）

#### 1. 启动服务

**Windows PowerShell:**
```powershell
.\start.ps1
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

**或手动启动:**
```bash
docker-compose -p conceptgraph up -d --build
```

#### 2. 访问系统

- **前端界面**: http://localhost:3000
- **后端API文档**: http://localhost:8000/docs
- **Neo4j数据库**: http://localhost:7474 (用户名: neo4j, 密码: conceptgraph123)

#### 3. 查看状态

```bash
# 查看容器状态
docker-compose -p conceptgraph ps

# 查看日志
docker-compose -p conceptgraph logs -f

# 停止服务
docker-compose -p conceptgraph down
```

### 方式二：本地开发环境

#### 前置要求

- Python 3.11+
- Node.js 18+
- Neo4j 5.15.0
- Redis 7.2+
- OpenRouter API Key
- OpenAI API Key

#### 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入必需配置
```

**.env 必需配置:**
```env
# OpenRouter API (LLM服务)
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# OpenAI API (Embedding服务)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# Neo4j配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### 启动数据库

```bash
# 启动Redis
docker run -d --name redis -p 6379:6379 redis:7.2-alpine

# 启动Neo4j
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.15.0
```

#### 启动后端

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 .\venv\Scripts\Activate.ps1  # Windows

# 安装依赖
pip install -r backend/requirements.txt

# 启动服务
python start_backend.py
```

#### 启动前端

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install --legacy-peer-deps

# 启动开发服务器
npm start
```

访问 http://localhost:3000 开始使用。

---

## 交付清单

### Dockerfile
- [backend/Dockerfile](backend/Dockerfile) - 后端Python 3.11-slim镜像
- [frontend/Dockerfile](frontend/Dockerfile) - 前端Node 18-alpine镜像
- [docker-compose.yml](docker-compose.yml) - 完整服务编排（4个容器）

### 依赖配置文件
- [requirements.txt](requirements.txt) - 根目录Python依赖
- [backend/requirements.txt](backend/requirements.txt) - 后端依赖（FastAPI, Neo4j, Redis, OpenAI等）
- [frontend/package.json](frontend/package.json) - 前端依赖（React 18, Ant Design 5, D3.js等）

### 完整源码

```
项目根目录/
├── backend/              # FastAPI后端服务
│   ├── api/              # API路由和业务逻辑
│   │   ├── routes.py     # 核心功能接口（三层缓存、多源融合）
│   │   ├── ai_chat.py    # LLM对话接口
│   │   ├── multi_function_generator.py  # 多功能生成器
│   │   └── real_node_generator.py       # 真实节点生成
│   ├── database/         # 数据库客户端
│   │   ├── neo4j_client.py  # Neo4j持久化操作
│   │   └── redis_client.py  # Redis缓存操作
│   ├── main.py           # FastAPI应用入口
│   ├── config.py         # 配置管理
│   └── Dockerfile        # 后端容器镜像
│
├── frontend/             # React前端应用
│   ├── src/
│   │   ├── App.tsx       # 主应用组件
│   │   ├── components/   # UI组件库
│   │   │   ├── GraphVisualization.tsx  # D3.js图可视化
│   │   │   └── NodeDetailPanel.tsx     # 节点详情面板
│   │   └── services/
│   │       └── api.ts    # 后端API调用服务
│   ├── package.json      # 前端依赖配置
│   └── Dockerfile        # 前端容器镜像
│
├── shared/               # 共享数据模型
│   ├── schemas/          # Pydantic数据模型
│   │   ├── concept_node.py   # 概念节点模型
│   │   ├── concept_edge.py   # 概念边模型
│   │   └── api_response.py   # API响应模型
│   ├── constants.py      # 常量定义（学科列表、关系类型）
│   └── utils.py          # 工具函数
│
├── prompts/              # LLM提示词模板
│   ├── discovery_prompts.py      # 概念发现提示词
│   ├── verification_prompts.py   # 知识验证提示词
│   ├── multi_function_prompts.py # 多功能提示词
│   └── prompt_config.json        # 提示词配置
│
├── algorithms/           # 核心算法模块
│   ├── semantic_similarity.py    # 语义相似度计算（OpenAI Embedding）
│   ├── discipline_classifier.py  # 学科分类器
│   ├── credibility_scorer.py     # 可信度评分
│   └── data_crawler.py           # Wikipedia/Arxiv数据爬取
│
├── agents/               # Agent编排系统（预留）
│   ├── orchestrator.py   # Agent编排器
│   ├── concept_discovery_agent.py
│   ├── verification_agent.py
│   └── graph_builder_agent.py
│
├── docker-compose.yml    # Docker服务编排
├── .env.example          # 环境变量模板
├── start.ps1             # Windows快速启动脚本
├── start.sh              # Linux/macOS快速启动脚本
└── start_backend.py      # 后端启动脚本
```

### 环境配置指南
- [ENVIRONMENT_SETUP(环境配置指南).md](ENVIRONMENT_SETUP（环境配置指南）.md) - 完整环境配置指南（系统要求、依赖安装、数据库配置、常见问题）
- [.env.example](.env.example) - 环境变量配置模板
- [start.ps1](start.ps1) / [start.sh](start.sh) - 跨平台快速启动脚本

---

## 系统架构

### 整体架构

```
┌─────────────────┐
│   React前端     │  (端口3000)
│   D3.js可视化   │
└────────┬────────┘
         │ HTTP请求
┌────────▼────────┐
│  FastAPI后端    │  (端口8000)
│  异步处理       │
└────────┬────────┘
         │
    三层缓存查询
  ┌─────┼─────┐
  ▼     ▼     ▼
Neo4j Redis  LLM+APIs
持久化 1小时  实时生成
```

### 数据流向（多源融合）

```
用户输入概念
    ↓
后端缓存检查
    ├─ Neo4j持久化数据 → 命中则返回
    ├─ Redis临时缓存 → 命中则返回
    └─ 缓存未命中 ↓
    
异步并行调用4个API
    ├─ OpenRouter API (Gemini Flash)
    │   └─ 生成初始概念图谱
    ├─ Wikipedia API
    │   └─ 获取权威定义和摘要
    ├─ Arxiv API
    │   └─ 搜索学术文献验证
    └─ OpenAI Embedding API
        └─ 计算语义相似度筛选
    ↓
数据融合与筛选
    └─ 相似度 > 0.6的高相关节点
    ↓
持久化存储
    ├─ 保存到Neo4j（永久存储）
    └─ 缓存到Redis（TTL 1小时）
    ↓
D3.js前端渲染
    └─ 力导向图可视化
```

---

## 功能使用

### 功能1：自动跨学科概念挖掘

1. 在首页输入框输入概念（如"熵"）
2. 点击"开始探索"按钮
3. 系统自动：
   - 检查Neo4j和Redis缓存
   - 若未命中，调用LLM生成初始图谱
   - 并行调用Wikipedia和Arxiv验证
   - 使用OpenAI Embedding计算语义相似度
   - 筛选相关度>0.6的节点
   - 保存到Neo4j和Redis
4. 查看D3.js力导向图可视化结果

### 功能2：指定学科挖掘

1. 选择学科（如"物理", "信息论", "计算机"）
2. 输入核心概念
3. 系统在指定学科范围内挖掘关联概念
4. 显示学科分类后的知识图谱

### 功能3：桥接概念发现

1. 输入多个概念（如"熵"和"量子纠缠"）
2. 设置最大桥接数量
3. 系统自动发现连接这些概念的"桥梁节点"
4. 显示桥接路径和reasoning说明

---

## API接口

### 概念发现

```http
POST /api/v1/discover
Content-Type: application/json

{
  "concept": "熵",
  "max_concepts": 30,
  "depth": 2
}
```

### 学科指定挖掘

```http
POST /api/v1/discover/disciplined
Content-Type: application/json

{
  "concept": "熵",
  "disciplines": ["物理", "信息论", "计算机"],
  "max_concepts": 30
}
```

### 桥接概念发现

```http
POST /api/v1/discover/bridge
Content-Type: application/json

{
  "concepts": ["熵", "量子纠缠"],
  "max_bridges": 5
}
```

### 清除缓存

```http
DELETE /api/v1/cache/clear?cache_type=all
```

**cache_type参数:**
- `redis` - 仅清除Redis缓存
- `neo4j` - 仅清除Neo4j数据
- `all` - 清除所有缓存

详细API文档访问：http://localhost:8000/docs

---

## 技术栈

### 后端技术
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 主要开发语言 |
| FastAPI | 0.109.0 | Web框架 |
| Neo4j | 5.15.0 | 图数据库（持久化存储） |
| Redis | 7.2 | 缓存数据库（1小时TTL） |
| Pydantic | 2.5.0 | 数据验证 |
| AsyncIO | - | 异步并发处理 |

### 前端技术
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18+ | UI框架 |
| TypeScript | 5.x | 类型系统 |
| Ant Design | 5.x | UI组件库 |
| D3.js | 7.x | 图可视化 |

### 云服务API
| 服务 | 用途 |
|------|------|
| OpenRouter API | LLM服务（Google Gemini Flash） |
| OpenAI Embedding API | 语义相似度计算（text-embedding-3-small） |
| Wikipedia API | 权威定义获取 |
| Arxiv API | 学术文献验证 |

### 部署技术
| 技术 | 版本 | 用途 |
|------|------|------|
| Docker | 24.x | 容器化 |
| Docker Compose | 2.20+ | 服务编排 |

---

## 文档

- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - 完整环境配置指南
- [NEO4J_USAGE.md](NEO4J_USAGE.md) - Neo4j使用说明
- [API文档](http://localhost:8000/docs) - 交互式API文档（Swagger UI）

---

## 开发指南

### 代码规范

```bash
# Python代码格式化
black backend/ --line-length 100
isort backend/

# Python代码检查
flake8 backend/
mypy backend/
```

### 提交规范

```bash
feat: 新功能
fix: Bug修复
docs: 文档更新
perf: 性能优化
refactor: 代码重构

# 示例
git commit -m "feat(api): 添加三层缓存架构"
git commit -m "fix(redis): 修复缓存参数错误"
```

---

## 性能优化

### 三层缓存效果

| 缓存层级 | 命中率 | 平均响应时间 |
|---------|-------|-------------|
| Neo4j | ~40% | < 100ms |
| Redis | ~30% | < 200ms |
| LLM实时生成 | ~30% | 8-15s |

### 异步并发优化

- 多源API调用采用AsyncIO并发处理
- 单次请求平均调用4个外部API
- 并发处理使响应时间减少60%以上

---

## 许可证

MIT License

---

## 联系方式

- **GitHub**: [kaifenger/Final_Cloud_Computing](https://github.com/kaifenger/Final_Cloud_Computing)
- **Issue**: 提交问题和建议

---

**ConceptGraph AI** - 基于多源融合的跨学科知识图谱系统
