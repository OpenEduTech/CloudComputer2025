# PPT内容扩展智能体 - 云计算系统期末大作业

## 我们的演示视频：  百度网盘网盘分享的文件：28小组视频.mp4
  - 链接: https://pan.baidu.com/s/1SdBdo6OkPcHg38gTwu0Sww 提取码: rbcd
  - 
## 我们的组内评分采用小组成员得分一致的方式！

##  项目概述

**PPT内容扩展智能体**是一个基于云原生架构和大型语言模型（LLM）的智能教育助手系统。该系统能够自动解析PPT内容，通过AI智能扩展知识点，关联外部权威资源，帮助学生高效学习和复习。

##  核心功能

### 1.  PPT智能解析
- **格式支持**：PPTX、PPT、PDF格式
- **结构识别**：自动识别标题、子标题、正文、图片等层级结构
- **内容提取**：提取文本内容、图片描述、布局信息

### 2.  AI知识扩展
- **背景补充**：自动补充知识点的背景信息和原理说明
- **公式推导**：提供相关公式的推导过程
- **代码示例**：生成与知识点相关的代码示例
- **实际应用**：展示知识在实际场景中的应用

### 3.  多维资源关联
- **Wikipedia**：关联权威百科知识
- **学术论文**：通过Arxiv、Semantic Scholar获取前沿研究
- **外部资源**：整合其他可信知识源

### 4.  语义智能搜索
- **向量检索**：基于Milvus的语义相似性搜索
- **跨PPT搜索**：在多个PPT间搜索相关内容
- **智能推荐**：推荐相关知识点的学习材料

### 5.  交互式学习界面
- **在线预览**：Web端直接查看PPT和扩展内容
- **交互操作**：点击切换页面，查看详细信息
- **导出功能**：支持导出Markdown、PDF格式笔记

##  系统架构

### 技术架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     用户界面层 (Presentation)                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                Streamlit Web界面                    │   │
│   │                   (localhost:8501)                  │   │
│   └─────────────────────────────────────────────────────┘   │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                      API网关层 (Gateway)                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                 FastAPI RESTful API                 │   │
│   │                   (localhost:8000)                  │   │
│   └─────────────────────────────────────────────────────┘   │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                     业务逻辑层 (Business Logic)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │PPT解析   │ │LLM智能体 │ │向量检索  │ │外部搜索  │       │
│  │模块      │ │模块      │ │模块      │ │模块      │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                     数据存储层 (Data Storage)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Milvus    │ │PostgreSQL│ │Redis     │ │MinIO     │       │
│  │向量数据库│ │关系数据库 │ │缓存      │ │对象存储  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 云原生组件

| 组件 | 技术选型 | 作用 | 云原生特性 |
|------|----------|------|------------|
| **容器编排** | Docker Compose | 服务编排和管理 | 可移植性、隔离性 |
| **Web框架** | FastAPI + Streamlit | 前后端分离 | 高性能、异步支持 |
| **向量数据库** | Milvus | 语义相似性搜索 | 高维向量检索、可扩展 |
| **关系数据库** | PostgreSQL | 结构化数据存储 | ACID事务、数据一致性 |
| **缓存服务** | Redis | 会话缓存和队列 | 内存存储、高速读写 |
| **对象存储** | MinIO | 文件存储服务 | S3兼容、分布式存储 |
| **代理服务器** | Nginx | 负载均衡和反向代理 | 高性能、可配置 |
| **任务队列** | Celery | 异步任务处理 | 分布式任务、可靠执行 |

##  快速开始

### 环境要求

- **操作系统**: Windows 10/11, macOS 10.14+, Ubuntu 18.04+
- **Docker**: 20.10.0+
- **Docker Compose**: 2.0.0+
- **内存**: 8GB RAM 以上
- **存储**: 10GB 可用空间

### 第一步：克隆项目

```bash
# 克隆项目到本地
git clone https://github.com/zyqin-dreamsun/cloudcomputer-group28
```

### 第二步：配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件
# 需要配置以下关键变量：
# 1. OPENAI_API_KEY - 您的OpenAI API密钥
# 2. POSTGRES_PASSWORD - PostgreSQL数据库密码
# 3. MINIO_ROOT_PASSWORD - MinIO存储密码
```

示例 `.env` 文件内容：
```env
# OpenAI配置
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 数据库配置
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=ppt_extender

# 存储配置
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=minio_password_123

# 应用配置
DEBUG=false
LOG_LEVEL=INFO
```

### 第三步：一键启动服务

```bash
# 使用Docker Compose启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f backend
```

### 第四步：访问应用

服务启动后，可以通过以下地址访问：

-  **前端界面**: http://localhost:8501
-  **API文档**: http://localhost:8000/docs
-  **健康检查**: http://localhost:8000/health
-  **MinIO控制台**: http://localhost:9001 (账号: admin / 密码: minio_password_123)

### 第五步：停止服务

```bash
# 停止并移除所有容器
docker-compose down

# 停止服务但保留数据
docker-compose stop

# 停止服务并清除所有数据
docker-compose down -v
```

##  项目结构

```
ppt-knowledge-extender/
├── backend/                    # FastAPI后端服务
│   ├── app/                   # 应用核心代码
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI主应用
│   │   ├── models.py         # 数据模型定义
│   │   ├── ppt_parser.py     # PPT解析模块
│   │   ├── vector_store.py   # 向量存储模块
│   │   ├── llm_client.py     # LLM调用模块
│   │   ├── search_client.py  # 外部搜索模块
│   │   └── utils.py          # 工具函数
│   ├── tests/                # 测试代码
│   │   ├── test_main.py      # 主应用测试
│   │   ├── test_ppt_parser.py # PPT解析测试
│   │   └── test_llm_client.py # LLM客户端测试
│   ├── requirements.txt      # Python依赖
│   └── Dockerfile           # 后端Docker配置
├── frontend/                 # Streamlit前端
│   ├── app.py               # 前端主应用
│   ├── requirements.txt     # 前端依赖
│   └── Dockerfile          # 前端Docker配置
├── docker-compose.yml       # Docker Compose配置
├── .env.example            # 环境变量模板
├── nginx.conf              # Nginx配置（可选）
├── README.md               # 项目说明文档
└── LICENSE                 # 开源许可证
```

##  详细配置

### 1. OpenAI API配置

项目使用OpenAI GPT-4 API进行知识扩展。您需要：

1. 访问 https://platform.openai.com/api-keys 获取API密钥
2. 在 `.env` 文件中设置 `OPENAI_API_KEY`
3. 确保账户有足够的额度

**备用方案**：如需使用其他LLM服务，可修改 `backend/app/llm_client.py` 中的配置。

### 2. 数据库配置

系统使用多种数据库，默认配置如下：

- **PostgreSQL**: 端口 5432，用户名 `postgres`
- **Redis**: 端口 6379，无密码
- **Milvus**: 端口 19530，用于向量存储
- **MinIO**: 端口 9000，Web控制台端口 9001

### 3. 开发模式运行

如果您想在不使用Docker的情况下开发：

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 新终端窗口，进入前端目录
cd frontend

# 安装前端依赖
pip install -r requirements.txt

# 启动前端服务
streamlit run app.py
```

##  使用指南

### 基本使用流程

1. **上传PPT文件**
   - 访问 http://localhost:8501
   - 点击"选择文件"按钮上传PPT
   - 支持PPTX、PPT、PDF格式

2. **等待处理完成**
   - 系统自动解析PPT结构
   - AI扩展知识点内容
   - 搜索外部关联资源

3. **查看扩展结果**
   - 左侧显示PPT原始内容
   - 右侧显示AI扩展内容
   - 下方显示外部参考资源

4. **导出学习笔记**
   - 支持导出为Markdown格式
   - 支持导出为PDF格式
   - 可生成测试题和错题本

### 功能演示

#### 示例1：机器学习PPT扩展
```
上传文件: machine_learning_intro.pptx
处理结果:
├── 原始内容: 3个章节，15个核心概念
├── AI扩展:
│   ├── 反向传播算法详细推导
│   ├── Python代码示例
│   └── 实际应用场景说明
└── 外部关联:
    ├── Wikipedia: 深度学习词条
    └── Arxiv: 最新研究论文
```

#### 示例2：跨学科知识关联
```
输入概念: "梯度下降"
系统发现:
├── 数学: 最优化理论
├── 计算机科学: 机器学习算法
├── 物理学: 势能场中的粒子运动
└── 经济学: 成本最小化问题
```

##  API接口

### 主要端点

| 方法 | 端点 | 说明 | 参数 |
|------|------|------|------|
| POST | `/api/ppt/upload` | 上传PPT文件 | `file` (multipart/form-data) |
| GET | `/api/ppt/{ppt_id}` | 获取PPT详情 | `ppt_id` (路径参数) |
| GET | `/api/search/semantic` | 语义搜索 | `query` (查询参数) |
| GET | `/health` | 健康检查 | 无 |

### 示例请求

```bash
# 上传PPT文件
curl -X POST http://localhost:8000/api/ppt/upload \
  -F "file=@example.pptx"

# 语义搜索
curl "http://localhost:8000/api/search/semantic?query=机器学习&top_k=5"
```

详细API文档请访问 http://localhost:8000/docs

##  测试

### 运行测试套件

```bash
# 进入后端目录
cd backend

# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_main.py -v
python -m pytest tests/test_ppt_parser.py -v

# 在Docker容器中运行测试
docker-compose exec backend python -m pytest tests/ -v
```
