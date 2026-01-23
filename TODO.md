# 长文本"事实卫士"智能体 - 项目开发指南

## 阶段一：基础架构搭建
### 模块1.1：项目初始化
**任务清单：**
- [x] 创建项目目录结构
  ```
  fact-guardian/
  ├── backend/
  │   ├── app/
  │   │   ├── __init__.py
  │   │   ├── main.py
  │   │   ├── models/
  │   │   ├── services/
  │   │   └── utils/
  │   ├── requirements.txt
  │   └── Dockerfile
  ├── frontend/ (后期)
  ├── docker-compose.yml
  └── README.md
  ```
- [x] 初始化 Git 仓库
- [x] 编写基础 README（项目描述、技术栈）

### 模块1.2：Docker环境配置
**任务清单：**
- [x] 编写 `backend/Dockerfile`
  - 基础镜像：`python:3.10-slim`
  - 安装依赖：FastAPI, uvicorn, python-docx, PyPDF2
- [x] 编写 `docker-compose.yml`
  - 服务：backend, redis
  - 端口映射：8000:8000
- [x] 测试容器启动：`docker-compose up`

**验收标准：**
Docker 容器成功启动，访问 `http://localhost:8000/docs` 能看到 FastAPI Swagger 文档

---

## 阶段二：核心功能实现

### 模块2.1：文档解析模块
**功能：** 支持上传 Word/PDF/TXT 文件并提取文本内容

**任务清单：**
- [x] 实现文件上传 API
  ```python
  # backend/app/main.py
  @app.post("/api/upload")
  async def upload_document(file: UploadFile)
  ```
- [x] 编写文档解析器
  - `backend/app/services/parser.py`
  - 支持 `.docx` (python-docx)
  - 支持 `.pdf` (PyPDF2/pdfplumber)
  - 支持 `.txt`
- [x] 文档分段逻辑（按章节/段落切分）

**验收标准：**
上传5000字以上文档，成功返回结构化文本（包含章节信息）

### 模块2.2：事实提取模块（核心）
**功能：** 使用 LLM 提取关键事实（数据、日期、结论、人名）

**任务清单：**
- [x] 集成 LLM API（Claude/GPT-4）
  - 配置 API Key（环境变量）
  - 封装调用函数 `backend/app/services/llm_client.py`
- [x] 设计 Prompt 模板
  ```python
  FACT_EXTRACTION_PROMPT = """
  请从以下文本中提取关键事实，包括：
  1. 数值数据（统计数字、百分比、金额等）
  2. 时间日期
  3. 重要结论/观点
  4. 人名、机构名
  
  输出格式为 JSON：
  {
    "facts": [
      {
        "type": "数据/日期/结论/人名",
        "content": "事实内容",
        "location": "章节/段落位置",
        "context": "上下文摘要"
      }
    ]
  }
  
  文本：{text}
  """
  ```
- [x] 实现事实提取 API
  ```python
  @app.post("/api/extract-facts")
  async def extract_facts(document_id: str)
  ```
- [x] 将提取的事实存入 Redis
  - Key: `facts:{document_id}`
  - Value: JSON 格式事实列表

**验收标准：**
对测试文档提取的事实准确率 > 80%，包含位置信息

### 模块2.3：冲突检测模块（核心）
**功能：** 检测文档内部前后矛盾的描述

**任务清单：**
- [x] 设计冲突检测 Prompt
  ```python
  CONFLICT_DETECTION_PROMPT = """
  以下是从同一文档不同位置提取的事实：
  
  事实A：{fact_a}
  位置：{location_a}
  
  事实B：{fact_b}
  位置：{location_b}
  
  请判断这两个事实是否存在冲突或矛盾。
  输出格式：
  {
    "has_conflict": true/false,
    "conflict_type": "数据不一致/逻辑矛盾/时间冲突",
    "severity": "高/中/低",
    "explanation": "冲突原因说明"
  }
  """
  ```
- [x] 实现成对事实比对逻辑
  - 同类型事实优先比对（如：两个关于"增长率"的数据）
- [x] 实现冲突检测 API
  ```python
  @app.post("/api/detect-conflicts")
  async def detect_conflicts(document_id: str)
  ```
- [x] 结果存储到 Redis
  - Key: `conflicts:{document_id}`

**验收标准：**
能检测出明显矛盾（如同一指标不同数值），误报率 < 20%

### 模块2.4：溯源校验模块（需要）
**功能：** 联网核实可疑事实的真实性

**任务清单：**
- [x] 集成搜索 API（Serper API / Tavily/Mock，当前使用 Mock 搜索，可替换真实搜索服务）
- [x] 实现自动搜索逻辑
  - 针对高冲突度的事实进行网络搜索
  - 提取权威来源（学术、官方网站）
- [x] 设计溯源验证 Prompt
  ```python
  VERIFICATION_PROMPT = """
  文档中声称：{claim}
  
  搜索结果：
  {search_results}
  
  请判断：
  1. 该声称是否得到搜索结果支持
  2. 可信度评级（高/中/低）
  3. 推荐的修正建议（如有必要）
  """
  ```
- [x] 实现溯源 API
  ```python
  @app.post("/api/documents/{document_id}/verify-facts")
  async def verify_facts(document_id: str, fact_ids: List[str])
  ```

**验收标准：**
对可验证的公开数据，能找到可靠来源并给出可信度评估

---

## 阶段三：扩展功能

### 模块3.1：参考文本对比功能 [补充功能]
**功能：** 上传参考文档，检测主文档与参考内容的相似度/引用关系

**任务清单：**
- [x] 扩展上传 API，支持多文件（主文档 + 参考文档）
- [x] 实现语义相似度计算
  - 方案A：使用 OpenAI Embeddings + 余弦相似度
  - 方案B：直接用 LLM 判断段落相似性
- [x] 设计对比 Prompt
  ```python
  COMPARISON_PROMPT = """
  主文档段落：{main_text}
  
  参考文档段落：{reference_text}
  
  请判断：
  1. 是否存在内容相似性（0-100%）
  2. 相似类型：直接引用/改写/思想借鉴/无关
  3. 如果是引用，是否需要标注来源
  """
  ```
- [x] 实现参考对比 API
  ```python
  @app.post("/api/compare-references")
  async def compare_with_reference(main_doc_id: str, ref_doc_ids: List[str])
  ```
- [x] 在结果中标注"相似段落"及其来源

**验收标准：**
能检测出明显的改写段落，相似度判断基本准确

### 模块3.2：图片/框架图对比 [补充功能]
**功能：** 上传框架图，检测文档描述与图片的一致性

**任务清单：**
- [x] 集成 OCR/图片理解 API（Claude Vision / GPT-4V）
- [x] 实现图片内容提取
  ```python
  @app.post("/api/extract-from-image")
  async def extract_image_content(file: UploadFile)
  ```
- [x] 设计图文对比 Prompt
  ```python
  IMAGE_TEXT_COMPARISON = """
  图片描述（由 AI 提取）：{image_description}
  
  文档相关段落：{document_text}
  
  请判断文档描述是否与图片内容一致，指出遗漏或矛盾之处。
  """
  ```

**验收标准：**
能识别基本框架图（如系统架构图），判断描述是否涵盖图中要素

---

## 阶段四：Web界面开发

### 模块4.1：前端框架搭建  [补充功能]
**技术栈：** React + Vite / Vue 3

**任务清单：**
- [x] 初始化前端项目
  ```bash
  npm create vite@latest frontend -- --template react
  ```
- [x] 安装依赖：axios, antd/mui（UI组件库）
- [x] 配置前端 Dockerfile

### 模块4.2：核心页面开发  [补充功能]
**页面1：文档上传页面**
- [x] 文件拖拽上传组件
- [x] 支持多文档上传（主文档 + 参考文档）
- [x] 上传进度显示

**页面2：分析结果展示页面**
- [x] 事实提取结果列表
  - 按类型（数据/日期/结论）分组展示
  - 点击定位到原文位置
- [x] 冲突检测结果
  - 高亮显示冲突事实对
  - 显示严重程度（红/黄/绿标签）
  - 展开查看详细说明
- [x] 参考对比结果（如已实现）
  - 相似段落并排对比视图
  - 相似度百分比可视化

**页面3：交互式编辑器** 

- [x] 在编辑器中实时标注冲突位置

**任务清单：**
- [x] 实现组件：`FileUpload.jsx`, `FactList.jsx`, `ConflictViewer.jsx`
- [x] 对接后端 API
- [x] 响应式布局适配

**验收标准：**
完整演示流程：上传文档 → 查看分析 → 查看冲突 → 导出报告

### 模块4.3：可视化仪表盘
**功能：** 展示文档健康度指标

**任务清单：**
- [x] 使用 ECharts/Recharts 绘制图表
  - 饼图：事实类型分布
  - 柱状图：各章节冲突密度
  - 折线图：文档版本对比（如有历史记录）
- [x] 实现"文档健康评分"算法
  ```python
  score = 100 - (冲突数 * 10) - (未验证事实数 * 2)
  ```

**验收标准：**
Dashboard 直观展示文档质量，有助于快速定位问题章节

---

## 阶段五：部署与文档

### 模块5.1：云原生优化
**任务清单：**
- [ ] Redis 持久化配置（RDB + AOF）
- [ ] 添加日志系统（Loguru）
- [ ] 实现健康检查端点
  ```python
  @app.get("/health")
  async def health_check()
  ```
- [ ] 性能测试（使用 Locust）
  - 目标：支持10并发文档分析

### 模块5.2：完善文档
**任务清单：**
- [x] 编写详细 README
  - 项目介绍
  - 快速开始（Docker 一键部署）
  - API 文档链接
  - 架构图（画图工具：draw.io）
- [ ] 编写技术文档（PDF/Markdown）
  - 架构设计：系统架构图、数据流图
  - 云原生组件说明：Docker, Redis, FastAPI
  - LLM Agent 设计：Prompt 模板、工具链
  - 分工说明：明确每人贡献
- [ ] 录制演示视频（3-5分钟）
  - 场景1：上传论文，展示事实提取
  - 场景2：查看冲突检测结果
  - 场景3：参考对比功能演示
  - 架构讲解（1分钟）

### 模块5.3：代码规范检查
**任务清单：**
- [x] 编写自动化集成测试脚本（test_auto.py）
  - 支持命令行参数区分测试模式（默认/图文对比/参考对比）
  - 覆盖所有核心API端点测试
  - 提供详细的测试报告输出
- [x] 运行代码格式化工具（Black, isort）
- [x] 添加类型注解（mypy）
- [x] 编写单元测试（pytest）
  - 测试文档解析
  - 测试事实提取（使用 Mock LLM）
- [x] Git 提交规范检查（Commitlint）


## 关键技术选型

### 后端
- **框架：** FastAPI（异步、高性能）
- **文档解析：** python-docx, pdfplumber
- **LLM API：** Claude API / OpenAI GPT-4
- **缓存/存储：** Redis（事实黑板）
- **搜索：** Serper API / Tavily（联网验证）

### 前端（如做 Web）
- **框架：** React + Vite / Vue 3
- **UI 组件：** Ant Design / Material-UI
- **可视化：** ECharts / Recharts
- **HTTP 客户端：** Axios

### DevOps
- **容器化：** Docker + Docker Compose
- **日志：** Loguru
- **测试：** Pytest

