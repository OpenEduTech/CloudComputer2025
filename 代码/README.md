# PPT知识扩展智能体

##  项目概述

基于云原生架构的PPT内容扩展智能体，能够自动解析PPT结构、补充相关知识、关联外部权威资源，帮助学生提升自学效率。

##  核心功能

1. **PPT语义解析** - 自动识别PPT的层级结构和内容
2. **知识智能扩展** - 调用LLM补充背景、公式、代码示例
3. **多维资源检索** - 联动Wikipedia、Arxiv、学术API
4. **向量语义搜索** - 基于Milvus的智能内容检索
5. **学习测试生成** - 自动生成测试题和错题本

##  系统架构
前端(Streamlit) → 后端(FastAPI) → 向量数据库(Milvus)
↑                    ↓               ↑
└───────── 外部API(LLM, Wikipedia, Arxiv)

##  快速开始

### 环境准备

1. 安装 Docker 和 Docker Compose
2. 克隆项目代码：
   ```bash
   git clone https://github.com/your-repo/ppt-knowledge-extender.git
   cd ppt-knowledge-extender
3. 配置环境变量
cp .env.example .env
编辑.env文件，填入您的OpenAI API Key等配置

### 启动
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend

### 项目结构
ppt-knowledge-extender/
├── backend/          # FastAPI后端服务
│   ├── app/         # 应用代码
│   ├── tests/       # 测试代码
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/        # Streamlit前端
│   ├── app.py
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md