

# 学习效果评估与巩固智能体 (Learning Assessment & Consolidation Agent)

## 项目简介 (Introduction)

**学习效果评估与巩固智能体** 是一个基于云计算和人工智能技术的现代化学习辅助系统，旨在实现 **"学-测-补"** 一体化的学习闭环，也就是资料上传（学）→ 智能考核（测）→ 错题分析（补）的业务闭环）。该系统利用大语言模型（LLM）和检索增强生成（RAG）技术，能够从用户上传的多模态学习资料（PDF文档、扫描件、录音音频）中自动提取核心考点，生成梯度化的试卷，进行智能判卷，并根据用户的答题情况提供个性化的错题分析和复习建议。

本系统遵循云原生（Cloud-Native）设计原则，采用微服务架构和容器化部署，确保系统的高可用性和弹性伸缩能力。

## 核心功能 (Key Features)

1.  **智能资料摄入 (Intelligent Ingestion)**
    *   支持 PDF 文档解析与 OCR 识别（集成 Qwen-VL 视觉模型）。
    *   支持音频录音文件的语音转文字（集成 FunASR）。
    *   自动提取文档/音频中的关键知识点。

2.  **梯度试卷生成 (Graded Quiz Generation)**
    *   基于 RAG 技术，动态生成涵盖核心考点的试卷。
    *   支持 **基础 (60%)**、**进阶 (30%)**、**挑战 (10%)** 三种难度梯度的题目分布。
    *   采用“考点驱动”策略，确保出题不跑题。

3.  **智能判卷系统 (Smart Grading)**
    *   **客观题**：混合判卷策略，逻辑硬匹配 + LLM 深度归因分析（针对错题）。
    *   **主观题**：基于 Prometheus 评分标准，从知识覆盖、逻辑连贯、准确性三个维度进行公平打分。

4.  **个性化错题本 & 仪表盘 (Mistake Dashboard)**
    *   自动记录错题，生成个性化错题本。
    *   可视化展示学习进度、错题分布和能力雷达图。
    *   支持错题导出和针对性巩固练习。

5.  **智能复习建议 (AI Tutor)**
    *   基于用户画像和历史答题数据，提供定制化的复习计划（长期和短期）和行动指南。

## 技术架构 (Architecture)
整体架构图：
![0625b80a5d7b0263056f9a1bec7d9511](assets/0625b80a5d7b0263056f9a1bec7d9511.jpg)

系统采用经典的三层架构，并结合了最新的 AI 技术栈：

*   **展示层 (Frontend)**: Streamlit, Plotly
*   **应用层 (Backend)**: Python, Flask, LangChain (CoT), OpenAI/Qwen API
*   **存储层 (Data)**: MongoDB (持久化), Redis (缓存), FAISS (向量检索)
*   **部署层 (Infra)**: Docker, Docker Compose, Kubernetes (Optional)

## 技术栈 (Tech Stack)

*   **Frontend**: Streamlit
*   **Backend**: Python 3.10+
*   **LLM Integration**: OpenAI API / 通义千问 (Qwen)
*   **Vector DB**: FAISS
*   **Database**: MongoDB (Replica Set), Redis (AOF enabled)
*   **Containerization**: Docker, Docker Compose
*   **Monitoring**: Prometheus, Grafana, ELK Stack

## 快速开始 (Getting Started)

### 环境要求

*   Docker 20.10+
*   Docker Compose 2.0+
*   Python 3.10+ (仅本地开发需要)

### 1. 配置环境变量

在项目根目录下创建一个 `.env` 文件，并填入以下配置：

```env
# OpenAI / 模型服务配置
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=your_api_base_url_here
OPENAI_CHAT_MODEL=ecnu-plus
OPENAI_EMBEDDING_MODEL=ecnu-embedding-small

# 数据库配置
MONGO_URI=mongodb://root:example@mongo:27017/study_agent_db?authSource=admin
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_password
```

### 2. 启动服务 (使用 Docker Compose)


```
# 打开容器
docker-compose exec app bash

# 启动所有服务
docker-compose up -d

# 安装依赖
pip install -r requirements.txt

# 启动应用
streamlit run app.py
```

### 3. 访问应用

服务启动后，在浏览器中访问：

```
http://localhost:8501
```

## 项目结构 (Project Structure)

```text
Cloud_project_v7
├─ .github/               # CI/CD workflows
├─ .env
├─ .streamlit
│  └─ config.toml
├─ app.py
├─ backend                # 后端核心逻辑
│  ├─ agents/             # AI Agents (出题、判卷)
│  │  ├─ base_agent.py
│  │  ├─ quiz_generator.py
│  │  └─ quiz_grader.py
│  ├─ config.py
│  ├─ dashboard_service.py # 仪表盘服务
│  ├─ database_service.py
│  ├─ ingestion_service.py # 资料摄入与RAG
│  └─ rag_service.py
├─ docker-compose.yml
├─ Dockerfile
├─ frontend/              # Streamlit 前端界面
│  ├─ auth_view.py        # 认证页面
│  ├─ dashboard_view.py   # 仪表盘页面
│  ├─ exam_view.py        # 考试页面
│  ├─ sidebar.py
│  └─ style.css
├─ init-mongo.js
├─ input/                 # 输入文件目录
├─ k8s/                   # Kubernetes 部署配置
│  ├─ api-gateway-deployment.yaml
│  ├─ app-deployment.yaml
│  ├─ configmaps.yaml
│  ├─ microservices-namespace.yaml
│  ├─ mistake-manager-deployment.yaml
│  ├─ mongodb-replica.yaml
│  ├─ namespace.yaml
│  ├─ quiz-generator-deployment.yaml
│  ├─ quiz-grader-deployment.yaml
│  ├─ redis-cluster.yaml
│  └─ secrets.yaml
├─ logging/               # ELK 日志栈配置
│  ├─ docker-compose.yml
│  ├─ filebeat
│  │  └─ filebeat.yml
│  ├─ kibana
│  │  └─ kibana.yml
│  ├─ logstash
│  │  ├─ config
│  │  │  └─ logstash.yml
│  │  └─ pipeline
│  │     └─ logstash.conf
│  └─ README.md
├─ microservices/         # 微服务模块
│  ├─ .env
│  ├─ docker-compose.yml
│  ├─ mistake_manager_service.py
│  ├─ nginx
│  │  └─ nginx.conf
│  ├─ quiz_generator_service.py
│  └─ quiz_grader_service.py
├─ monitoring/            # Prometheus & Grafana 监控配置
│  ├─ alertmanager
│  │  └─ alertmanager.yml
│  ├─ alerts
│  │  └─ learning-agent-alerts.yml
│  ├─ docker-compose.yml
│  ├─ grafana
│  │  └─ provisioning
│  │     ├─ dashboards
│  │     │  └─ learning_agent_dashboard.json
│  │     └─ datasources
│  │        └─ prometheus.yml
│  ├─ prometheus
│  │  └─ prometheus.yml
│  ├─ prometheus.yml
│  └─ README.md
├─ project_tree.md
├─ requirements.txt
├─ static
├─ 说明文档（README）/     # 详细文档目录
│   ├─ API_DOCUMENTATION.md
│  ├─ ARCHITECTURE.md
│  ├─ DEPLOYMENT_GUIDE.md
│  ├─ KUBERNETES_DEPLOYMENT.md
│  ├─ README.md
│  └─ TESTING_GUIDE.md
├─ app.py                 # 应用入口
├─ docker-compose.yml     # Docker 编排文件
├─ Dockerfile             # 应用镜像构建
├─ requirements.txt       # Python 依赖
└─ 技术报告.md             # 详细架构与技术报告

```

## 贡献

| 角色          | 何峻伟（算法/Agent组，35%）                          | 黄煜（算法/Agent组，35%）                          | 安雪娇（架构/工程组，30%）                          |
|---------------|-----------------------------------------------------|-----------------------------------------------------|-----------------------------------------------------|
| 核心职责      | 负责pdf读取、LLM出题与判卷逻辑                               | 负责录音读取、考点提取、错题管理与个性化复习                          | 负责存储架构+前端交互+部署优化                       |
| 具体工作      | 1. pdf的读取（包括扫描件）；2. 设计考点提取+出题Prompt（确保覆盖核心知识点）；3. 开发Prometheus判卷提示词；4. 主观题解析生成逻辑 | 1. 录音读取与考点读取；2. 难度分级规则库设计；3. 错题数据结构（关联考点/章节）；4. 个性化复习建议生成Prompt | 1. 搭建Redis+MongoDB存储集群；2. 开发Web答题界面（支持上传资料/答题/查看错题）；3. 编写Docker配置+环境部署文档；4. 测试高并发场景（如多用户同时答题） |
