# 学习效果评估与巩固智能体

## 项目简介

学习效果评估与巩固智能体是一个基于云计算和人工智能技术的学习辅助系统，旨在实现"学-测-补"一体化的学习闭环。该系统能够从用户上传的学习资料中提取核心考点，生成梯度化试卷，进行智能判卷，并为用户提供个性化的错题本和复习建议。

## 成员分工
| 角色          | 何俊伟（算法/Agent组，35%）                          | 黄煜（算法/Agent组，35%）                          | 安雪娇（架构/工程组，30%）                          |
|---------------|-----------------------------------------------------|-----------------------------------------------------|-----------------------------------------------------|
| 核心职责      | 负责LLM出题与判卷逻辑                               | 负责考点提取与错题管理模块                           | 负责存储架构+前端交互+部署优化                       |
| 具体工作      | 1. 设计考点提取+出题Prompt（确保覆盖核心知识点）；2. 开发Prometheus判卷提示词；3. 主观题解析生成逻辑 | 1. 难度分级规则库设计；2. 错题数据结构化（关联考点/章节）；3. 个性化复习建议生成Prompt | 1. 搭建Redis+MongoDB存储集群；2. 开发Web答题界面（支持上传资料/答题/查看错题）；3. 编写Docker配置+环境部署文档；4. 测试高并发场景（如多用户同时答题） |


## 功能特性

1. **智能资料摄入**：支持PDF文档和录音音频的解析与处理
2. **梯度试卷生成**：基于学习资料生成基础、进阶、挑战三个难度级别的试卷
3. **智能判卷系统**：客观题自动比对答案，主观题基于LLM进行评分和解析
4. **个性化错题本**：记录用户高频错误，提供难度分布统计和错题导出功能
5. **数据可视化**：展示答题进度、错题统计和难度分布图表

## 技术栈

- **前端框架**：Streamlit
- **后端框架**：Python
- **大语言模型**：OpenAI API / 通义千问API
- **向量存储**：FAISS
- **数据库**：MongoDB（持久化存储）+ Redis（缓存）
- **容器化**：Docker + Docker Compose

## 环境准备

### 系统要求

- Windows / macOS / Linux
- Docker 20.10+ 
- Docker Compose 2.0+
- Python 3.10+


## 项目配置

### 1. 环境变量配置

创建一个`.env`文件，添加以下配置：

```env
# OpenAI API配置
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=your_api_base_url_here
OPENAI_CHAT_MODEL=ecnu-plus
OPENAI_EMBEDDING_MODEL=ecnu-embedding-small

# 数据库配置
MONGO_URI=mongodb://root:example@localhost:27017/study_agent_db?authSource=admin
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password
```

### 2. 依赖安装（可选，本地运行时需要）

```bash
pip install -r requirements.txt
```

## 运行方式

### 1. 使用Docker Compose（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 停止所有服务
docker-compose down

# 重启所有服务
docker-compose restart
```

### 2. 本地运行（开发环境）

```bash
# 启动MongoDB和Redis容器
docker-compose up -d mongo redis

# 运行应用
streamlit run app.py
```


## 使用说明

### 1. 上传学习资料

- 在左侧边栏选择资料类型（PDF文档或录音音频）
- 点击"浏览文件"上传学习资料
- 点击"开始处理"按钮解析资料

### 2. 生成试卷

- 资料解析成功后，点击"生成一套梯度试卷"按钮
- 系统会自动分析考点并生成基础、进阶、挑战三个难度级别的题目

### 3. 答题与提交

- 按照题目顺序进行答题
- 可以使用"保存答案草稿"功能保存当前答题进度
- 完成所有题目后，点击"提交试卷"按钮

### 4. 查看结果与错题本

- 系统会自动判卷并显示得分和解析
- 可以在"错题仪表盘"查看个性化错题本
- 支持按难度筛选错题和导出错题本

### 5. 个性化复习
系统允许用户查看用户薄弱考点，并生成复习题目3题

## 项目结构

```
.
├── backend/              # 后端代码
│   ├── agents/           # 智能体模块
│   ├── config.py         # 配置文件
│   ├── database_service.py # 数据库服务
│   ├── ingestion_service.py # 资料摄入服务
│   └── rag_service.py    # RAG服务
├── frontend/             # 前端代码
│   ├── dashboard_view.py # 错题仪表盘
│   ├── exam_view.py      # 考试界面
│   └── sidebar.py        # 侧边栏
├── data/                 # 数据目录
│   ├── mongo/            # MongoDB数据
│   └── redis/            # Redis数据
├── temp/                 # 临时文件目录
├── app.py                # 应用入口
├── docker-compose.yml    # Docker Compose配置
├── Dockerfile            # Docker镜像构建文件
├── requirements.txt      # Python依赖
└── .env                  # 环境变量配置
```
