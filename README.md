# 智能学习与算法评估平台

基于 **多智能体协作**、**多模态 RAG**、**知识图谱** 的下一代智能化学习评估系统。  
支持自动出题、智能判卷、错题本、个性化学习路径、LeetCode 算法专题辅导、学术论文解析、代码实践与防幻觉校验。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-brightgreen)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue)](https://react.dev/)
[![Docker](https://img.shields.io/badge/docker-enabled-blue?logo=docker)](https://www.docker.com/)

## 项目分工
本次提交的代码主要面向「008 分支」的 [RAG功能] 开发，参与人员及核心职责如下：

| 人员/账号       | 核心职责                                                                                                                                                                                                 | 负责文件/模块范围                                                                                                                                                                                                 |
|----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| lwq-NEWCEO（罗文琦） | 1. **智能体策略与 RAG 核心逻辑**：独立设计全套 Prompt 模板（问答/难度梯度出题/元认知校验）、实现 CoT 思维链推理链路、开发 SafetyChecker 容错校验层（checker.py）解决大模型幻觉问题；<br>2. **云原生架构实施**：完成全系统 Docker 容器化封装（编写 Dockerfile/docker-compose.yml）、落地前后端分离微服务架构（Nginx 反向代理+FastAPI 异步服务）；<br>3. **前端可视化开发**：开发支持 Markdown/LaTeX 渲染的 Chat 组件（流式响应+多模态展示）、基于 React Force Graph 的动态知识图谱组件（节点拖拽/缩放/点击交互）；<br>4. **数据工程与交付**：重构 LeetCode 爬虫/多模态解析/向量库/图谱建库脚本、编写 GitHub README 与 Demo 视频素材；<br>5. **知识库与问答系统搭建**：构建 ChromaDB 向量库+Neo4j 图数据库双路知识库、实现 RAG 知识问答系统与难度梯度智能出题功能 | `scripts/` 目录：<br>  - leetcode-crawler.py（LeetCode 题目爬取+MD 转换）<br>  - parse_pdf_multimodal.py（PDF/MD 解析+图片处理+生成 parsed_docs.jsonl）<br>  - build_index_ollama.py（调用 Nomic-embed-text 生成向量+ChromaDB 建库）<br>  - build_leetcode_graph.py（MD 元数据提取+Neo4j 图谱构建）<br><br>`services/agent/` 目录：<br>  - checker.py（SafetyChecker 容错校验层核心代码）<br>  - rag_demo.py（FastAPI 后端入口+静态资源挂载+API 接口实现）<br><br>`frontend/src/components/` 目录：<br>  - Chat.tsx（沉浸式对话组件：Markdown/KaTeX 渲染+代码高亮+引用展示）<br>  - GraphView.tsx（知识图谱可视化组件：响应式布局+节点交互）<br><br>其他核心目录/文件：<br>  - `index/chroma/`（ChromaDB 向量存储持久化目录）<br>  - `docs/`（LeetCode 题目 MD 源文件+本地图片存储，按 easy/mid/hard 分类）<br>  - `data/`（parsed_docs.jsonl 中间数据+extracted_images 解析图片归档）<br>  - 项目根目录：Dockerfile、docker-compose.yml（容器化配置）、README.md（项目文档） |
| 孙嘉 | 其余部分前后端编写，包括智能出题、多维度智能判卷、知识图谱可视化、 错题本 & 针对性推荐、主页面                                                        | 其余文件 |





## 项目愿景与核心价值

我们希望打造一个 **“从上传资料 → 智能出题 → 个性化判卷与反馈 → 知识图谱跟踪 → 针对性复习”** 的闭环智能学习平台，同时深度垂直支持 **LeetCode 刷题** 与 **计算机学术论文** 阅读理解。

主要解决痛点：

- 传统刷题平台知识点碎片化、缺乏系统性关联
- 通用大模型容易产生幻觉、引用不准确
- 学习者难以快速定位薄弱点并获得高质量个性化指导
- 缺少多模态（文字+代码+图表+公式）理解能力

## ✨ 项目亮点

- **真正的闭环个性化学习**  
  从上传资料 → 自动解析建库 → 精准识别薄弱点 → 动态生成针对性题目 → 多维度智能判卷 → 知识图谱实时跟踪 → 错题专项强化，形成完整学习闭环

- **多模态 RAG + 知识图谱双轮驱动**  
  支持 PDF 表格/公式/图表、Markdown 图片引用、LeetCode 题目结构化解析，同时结合向量检索（ChromaDB）与结构化推理（Neo4j），回答更精准、知识关联更清晰

- **强防幻觉设计（三级护栏）**  
  检索熔断（无召回直接拒绝） + 强制证据引用（[evidence:xx]） + 质量过滤（长度/重复/拒答检测），大幅降低大模型胡说八道风险，特别适合教育场景

- **多智能体协作判卷**  
  采用 Prometheus 风格多 Agent 评分（生成 → 初评 → 审核 → 综合反馈），提供详细、可落地的改进建议，而非简单对错

- **LeetCode + 通用学习双垂直支持**  
  一套系统同时满足：  
  • 算法刷题党（LeetCode 爬取、标签图谱、代码题生成与执行）  
  • 通用学科学习者（教材/论文/笔记 → 智能出题与辅导）

- **沉浸式前端体验**  
  React + Vite + Monaco Editor + Force Graph + Markdown/LaTeX 实时渲染 + 流式对话 + 知识图谱交互，让学习过程更像「和 AI 导师一起刷题/复习」

- **完全云原生 & 一键部署**  
  全 Docker Compose 编排，支持通义千问 / OpenAI / Ollama 本地模型切换，开发、测试、生产环境一致性极高

- **数据处理流水线完整开源**  
  LeetCode 爬虫、多模态 PDF 解析、向量/图谱构建脚本全部开源，可复用、可扩展，适合二次开发或学术研究


## ✨ 核心功能一览

| 功能模块               | 描述                                                                 | 支持多模态 | 防幻觉机制 | 个性化程度 |
|-----------------------|----------------------------------------------------------------------|------------|------------|------------|
| 智能出题              | 根据知识库 / LeetCode / 薄弱点自动生成单选、简答、代码题               | ✓          | —          | ★★★★★      |
| 多维度智能判卷        | 多 Agent 协作评分 + 详细反馈 + 改进建议（Prometheus 风格）             | ✓          | ✓          | ★★★★★      |
| 知识图谱可视化        | 实时构建 & 展示知识点关系（难度 ↔ 标签 ↔ 题目 ↔ 掌握度）              | —          | —          | ★★★★☆      |
| 错题本 & 针对性推荐   | 自动记录错题 → 分析薄弱链路 → 生成专项复习题                           | ✓          | —          | ★★★★★      |
| RAG 增强智能对话      | 基于知识库的沉浸式问答，支持 LaTeX、代码高亮、表格、图片引用          | ✓✓         | ✓✓✓        | ★★★★☆      |
| LeetCode 垂直域支持   | 爬取题目 → 多模态解析 → 图谱构建 → 专题训练 & 思路引导                | ✓✓         | ✓✓         | ★★★★★      |
| 学术论文 / PDF 理解   | 支持表格、公式、图表的多模态检索与解释                                | ✓✓✓        | ✓✓         | ★★★★☆      |
| 代码实践与执行        | 生成编程题 → 在线 Monaco 编辑器 → 安全沙箱执行                        | ✓          | —          | ★★★★☆      |

## 🏗 系统架构



## 🎨 前端展示（UI/UX 设计与页面构成）

目前项目采用 **React 18 + Vite** 作为前端技术栈，UI 组件库主要使用 **Ant Design 5**（部分页面实验 Material UI），强调**沉浸式、响应式、可视化**的学习体验。

### 主要页面与功能预览

#### （详细介绍和效果展示请移步技术文档）


1. **仪表盘 / 学习概览**  
   - 知识掌握度环形图 / 知识点热力图  
   - 最近错题 Top 5（可点击快速复习）  
   - 推荐学习路径（卡片流 / 时间轴式）  
   - 今日学习统计（学习时长 / 完成题量 / 正确率趋势）
   - 
  <img width="1836" height="1043" alt="image" src="https://github.com/user-attachments/assets/715a01a5-0170-43e2-9dbb-f612f0b0c9aa" />
  
<img width="2555" height="1453" alt="fe2910d7d4f16b1d6189fe6933c5da0b" src="https://github.com/user-attachments/assets/772af6d6-2ac6-45fb-a451-f351738a4153" />


2. **知识库管理**  
   - 支持拖拽上传 PDF / Markdown / TXT / 图片  
   - 实时文档解析进度条 + 状态提示  
   - 已索引文档列表（支持搜索、预览、删除）

3. **智能出题中心**  
   - 出题参数控制面板（题型、难度、数量、是否专注薄弱点）  
   - 生成过程中流式显示题目（loading + 逐题出现动画）  
   - 支持单题练习 / 整套小测验 / 定时模式

4. **答题 & 判卷界面**  
   - 题目展示支持富文本 + LaTeX 公式 + 代码高亮  
   - 交互组件：单选、多选、填空、简答、代码编辑（Monaco Editor）  
   - 提交后立即展示：得分 + 多维度反馈 + 证据引用链  
   - 一键“我不会” → 呼出 AI 详细讲解（可继续追问）

5. **知识图谱浏览器**  
   - 力导向图实现（推荐 React Force Graph 或 D3.js）  
   - 支持缩放、拖拽、节点/边高亮、路径追踪  
   - 点击节点展开：相关题目列表、当前掌握度、错题记录  
   - 薄弱知识点红色高亮 + 一键生成推荐学习链路

6. **AI 智能助教对话**  
   - 支持全屏沉浸模式 / 右侧抽屉模式  
   - 流式输出，支持 Markdown 表格、代码块、LaTeX 公式渲染  
   - 自动带入上下文（当前题目、知识库片段、错题历史）  
   - 可显示证据引用编号 `[evidence:12]` 并支持点击跳转查看原文

7. **错题本 & 专项复习**  
   - 按知识点 / 标签 / 难度 / 出错次数 多维度分类  
   - 一键生成“薄弱点专项训练”套题  
   - 历史错题趋势折线图 + 掌握度提升曲线

## 📂 项目结构
```text
CloudComputer2025/
├── frontend/                     # 前端代码
│   ├── public/                   # 静态资源
│   ├── src/                      # 前端源码
│   │   ├── components/           # 可复用组件
│   │   ├── pages/                # 页面组件
│   │   ├── services/             # 前端服务（API 调用）
│   │   ├── state/                # 状态管理（如 Zustand）
│   │   ├── utils/                # 工具函数
│   │   ├── App.jsx               # 应用入口
│   │   └── index.jsx             # React 渲染入口
│   ├── package.json              # 前端依赖
│   └── vite.config.js            # Vite 配置
├── backend/                      # 后端代码
│   ├── app/                      # FastAPI 应用
│   │   ├── routes/               # API 路由
│   │   │   ├── auth.py           # 认证授权
│   │   │   ├── upload.py         # 文件上传
│   │   │   ├── questions.py      # 题目生成
│   │   │   ├── grading.py        # 判卷服务
│   │   │   ├── knowledge.py      # 知识图谱
│   │   │   └── chat.py           # AI 对话
│   │   ├── services/             # 业务逻辑
│   │   │   ├── question_generator.py  # 题目生成服务
│   │   │   ├── grading_service.py     # 判卷服务
│   │   │   ├── rag_service.py         # RAG 检索服务
│   │   │   ├── knowledge_graph.py     # 知识图谱服务
│   │   │   └── chat_service.py        # 对话服务
│   │   ├── models/               # 数据模型
│   │   ├── utils/                # 工具函数
│   │   ├── config.py             # 配置文件
│   │   └── main.py               # 应用入口
│   ├── tests/                    # 后端测试
│   ├── requirements.txt          # Python 依赖
│   └── Dockerfile                # 后端 Docker 配置
├── database/                     # 数据库相关
│   ├── migrations/               # 数据库迁移脚本
│   ├── init/                     # 初始化脚本
│   ├── mongo/                    # MongoDB 配置
│   ├── chroma/                   # ChromaDB 配置
│   └── neo4j/                    # Neo4j 配置
├── ai_services/                  # AI 服务
│   ├── agents/                   # 智能体逻辑
│   │   ├── question_agent.py     # 题目生成 Agent
│   │   ├── grading_agent.py      # 判卷 Agent
│   │   ├── knowledge_agent.py    # 知识图谱 Agent
│   │   └── chat_agent.py         # 对话 Agent
│   ├── prompts/                  # Prompt 模板
│   │   ├── question_prompt.txt   # 题目生成 Prompt
│   │   ├── grading_prompt.txt    # 判卷 Prompt
│   │   └── chat_prompt.txt       # 对话 Prompt
│   ├── embeddings/               # 嵌入向量相关
│   └── llm_client.py             # LLM API 客户端
├── deployment/                   # 部署相关
│   ├── docker-compose.yml        # Docker Compose 配置
│   ├── k8s/                      # Kubernetes 配置
│   │   ├── frontend-deployment.yaml
│   │   ├── backend-deployment.yaml
│   │   ├── mongodb-deployment.yaml
│   │   ├── chromadb-deployment.yaml
│   │   └── neo4j-deployment.yaml
│   ├── scripts/                  # 部署脚本
│   └── README.md                 # 部署说明
├── tests/                        # 集成测试
│   ├── frontend/                 # 前端测试
│   ├── backend/                  # 后端测试
│   └── e2e/                      # 端到端测试
├── docs/                         # 文档
│   ├── TECHNICAL_DOCUMENTATION.md # 技术文档
│   ├── API_REFERENCE.md          # API 文档
│   └── DEPLOYMENT_GUIDE.md       # 部署指南
├── .env                          # 环境变量配置
├── .gitignore                    # Git 忽略文件
└── README.md                     # 项目说明project-root/
├── frontend/                     # 前端代码
│   ├── public/                   # 静态资源
│   ├── src/                      # 前端源码
│   │   ├── components/           # 可复用组件
│   │   ├── pages/                # 页面组件
│   │   ├── services/             # 前端服务（API 调用）
│   │   ├── state/                # 状态管理（如 Zustand）
│   │   ├── utils/                # 工具函数
│   │   ├── App.jsx               # 应用入口
│   │   └── index.jsx             # React 渲染入口
│   ├── package.json              # 前端依赖
│   └── vite.config.js            # Vite 配置
├── backend/                      # 后端代码
│   ├── app/                      # FastAPI 应用
│   │   ├── routes/               # API 路由
│   │   │   ├── auth.py           # 认证授权
│   │   │   ├── upload.py         # 文件上传
│   │   │   ├── questions.py      # 题目生成
│   │   │   ├── grading.py        # 判卷服务
│   │   │   ├── knowledge.py      # 知识图谱
│   │   │   └── chat.py           # AI 对话
│   │   ├── services/             # 业务逻辑
│   │   │   ├── question_generator.py  # 题目生成服务
│   │   │   ├── grading_service.py     # 判卷服务
│   │   │   ├── rag_service.py         # RAG 检索服务
│   │   │   ├── knowledge_graph.py     # 知识图谱服务
│   │   │   └── chat_service.py        # 对话服务
│   │   ├── models/               # 数据模型
│   │   ├── utils/                # 工具函数
│   │   ├── config.py             # 配置文件
│   │   └── main.py               # 应用入口
│   ├── tests/                    # 后端测试
│   ├── requirements.txt          # Python 依赖
│   └── Dockerfile                # 后端 Docker 配置
├── database/                     # 数据库相关
│   ├── migrations/               # 数据库迁移脚本
│   ├── init/                     # 初始化脚本
│   ├── mongo/                    # MongoDB 配置
│   ├── chroma/                   # ChromaDB 配置
│   └── neo4j/                    # Neo4j 配置
├── ai_services/                  # AI 服务
│   ├── agents/                   # 智能体逻辑
│   │   ├── question_agent.py     # 题目生成 Agent
│   │   ├── grading_agent.py      # 判卷 Agent
│   │   ├── knowledge_agent.py    # 知识图谱 Agent
│   │   └── chat_agent.py         # 对话 Agent
│   ├── prompts/                  # Prompt 模板
│   │   ├── question_prompt.txt   # 题目生成 Prompt
│   │   ├── grading_prompt.txt    # 判卷 Prompt
│   │   └── chat_prompt.txt       # 对话 Prompt
│   ├── embeddings/               # 嵌入向量相关
│   └── llm_client.py             # LLM API 客户端
├── deployment/                   # 部署相关
│   ├── docker-compose.yml        # Docker Compose 配置
│   ├── k8s/                      # Kubernetes 配置
│   │   ├── frontend-deployment.yaml
│   │   ├── backend-deployment.yaml
│   │   ├── mongodb-deployment.yaml
│   │   ├── chromadb-deployment.yaml
│   │   └── neo4j-deployment.yaml
│   ├── scripts/                  # 部署脚本
│   └── README.md                 # 部署说明
├── tests/                        # 集成测试
│   ├── frontend/                 # 前端测试
│   ├── backend/                  # 后端测试
│   └── e2e/                      # 端到端测试
├── docs/                         # 文档
│   ├── TECHNICAL_DOCUMENTATION.md # 技术文档
│   ├── API_REFERENCE.md          # API 文档
│   └── DEPLOYMENT_GUIDE.md       # 部署指南
├── .env                          # 环境变量配置
├── .gitignore                    # Git 忽略文件
└── README.md                     # 项目说明
```


## 🚀 快速开始

### 环境要求

- Docker & Docker Compose  
- LLM API Key（支持：通义千问 / OpenAI / Ollama 本地模型）

### 一键启动（推荐方式）

```bash
git clone https://github.com/lwq-NEWCEO/CloudComputer2025.git
cd CloudComputer2025

# 选择你想使用的 LLM 环境的 env 示例文件
cp .env.qwen.example .env
# 或 cp .env.openai.example .env
# 或 cp .env.ollama.example .env

# 编辑 .env 文件填入你的 API Key / 模型地址 等配置
docker compose up -d --build

### 默认访问地址

前端界面：http://localhost:3000 或 http://localhost
API 文档：http://localhost:8000/docs 或 http://localhost:8088/docs
Neo4j Browser：http://localhost:7474 （默认账号 neo4j / 密码 password123）
```
---

## 👥 贡献 


本项目工作量涵盖以下四个维度：

* **云原生架构设计**: Docker 容器化配置、Docker Compose 服务编排、K8s 适配性方案预研。
* **智能体策略开发**: Prompt 工程设计、RAG 推理链路 (CoT) 优化、容错校验层 (Checker) 开发。
* **全栈工程开发**: React 可视化前端开发、FastAPI 后端微服务开发。
* **数据流水线建设**: 爬虫工程化、多模态数据清洗、知识库构建脚本编写。

---

## 📜 致谢

本项目在开发过程中使用了以下开源项目：

* [Ollama](https://ollama.com/)
* [LangChain](https://www.langchain.com/)
* [React Force Graph](https://github.com/vasturiano/react-force-graph)
* [ChromaDB](https://www.trychroma.com/)
* [LeetCode](https://leetcode.com/) (数据来源)
--- 
