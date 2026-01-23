# PPTAS 系统详细使用说明

## 目录

1. [系统简介](#系统简介)
2. [环境准备](#环境准备)
3. [安装与配置](#安装与配置)
4. [快速开始](#快速开始)
5. [功能详解](#功能详解)
6. [API 接口文档](#api-接口文档)
7. [配置说明](#配置说明)
8. [数据管理](#数据管理)
9. [故障排除](#故障排除)
10. [高级用法](#高级用法)

---

## 系统简介

PPTAS（PPT 智能扩展系统）是一个基于 AI Agent 技术的智能学习辅助系统，能够自动分析 PPT 文档，识别知识缺口，并提供结构化的学习笔记和补充说明。

### 核心功能

- **文档解析**: 支持 PPTX 和 PDF 格式，自动提取文本和结构
- **全局分析**: 分析整个文档的主题、章节结构和知识点框架
- **单页分析**: 对单个页面进行深度分析，包括知识聚类、理解笔记生成、知识缺口识别等
- **知识扩展**: 为识别的知识缺口生成补充说明和参考资料
- **数据持久化**: 分析结果自动保存到数据库，支持缓存和查询

### 系统架构

```
前端 (Vue 3) ←→ API 层 (FastAPI) ←→ 服务层 ←→ Agent 层 (LangGraph) ←→ 数据层 (SQLite)
```

---

## 环境准备

### 系统要求

- **操作系统**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python**: 3.9 或更高版本
- **Node.js**: 16.0 或更高版本
- **Docker**: 可选，用于容器化部署

### 必需软件

1. **Python 环境**
   - 推荐使用 Conda 或 venv 创建虚拟环境
   - 安装 Python 3.9+

2. **Node.js 环境**
   - 安装 Node.js 16.0+
   - 安装 npm 或 yarn

3. **LibreOffice**（用于 PPTX 预览）
   - Windows: 从 https://www.libreoffice.org/ 下载安装
   - Linux: `sudo apt-get install libreoffice`
   - macOS: `brew install --cask libreoffice`

4. **Docker**（可选，用于容器化部署）
   - Windows/Mac: Docker Desktop
   - Linux: Docker Engine

---

## 安装与配置

### 步骤 1: 克隆仓库

```bash
git clone <repository-url>
cd PPTAS
```

### 步骤 2: 后端环境配置

#### 2.1 创建 Python 虚拟环境

```bash
# 使用 Conda
conda create -n PPTAS python=3.9
conda activate PPTAS

# 或使用 venv
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

#### 2.2 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 2.3 配置 LLM

编辑 `backend/config.json`:

```json
{
  "llm": {
    "api_key": "your-api-key",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
  },
  "retrieval": {
    "preferred_sources": ["arxiv", "wikipedia"],
    "max_results": 3,
    "local_rag_priority": true
  },
  "expansion": {
    "max_revisions": 2,
    "min_gap_priority": 3,
    "temperature": 0.7
  },
  "streaming": {
    "enabled": true,
    "chunk_size": 50
  },
  "knowledge_base": {
    "path": "./knowledge_base",
    "chunk_size": 1000,
    "chunk_overlap": 200
  },
  "vector_store": {
    "path": "./ppt_vector_db",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "embedding_model": "BAAI/bge-m3"
  }
}
```

**配置说明**:

- `llm.api_key`: LLM API 密钥（必需）
- `llm.base_url`: LLM API 基础 URL（必需）
- `llm.model`: 使用的模型名称（必需）
- `retrieval.preferred_sources`: 优先使用的知识源列表
- `retrieval.max_results`: 每个知识源的最大结果数
- `expansion.max_revisions`: 最大修订次数
- `expansion.min_gap_priority`: 最小缺口优先级

**支持的 LLM 提供商**:

- OpenAI: `base_url: "https://api.openai.com/v1"`, `model: "gpt-4"`
- SiliconFlow: `base_url: "https://api.siliconflow.cn/v1"`, `model: "deepseek-ai/DeepSeek-V3.2-Exp"`
- 其他 OpenAI 兼容接口

#### 2.4 环境变量配置（可选）

除了配置文件，也可以通过环境变量设置：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4"
```

### 步骤 3: 前端环境配置

#### 3.1 安装前端依赖

```bash
cd frontend
npm install
```

#### 3.2 前端配置

前端配置在 `frontend/vite.config.js` 中，通常无需修改。如需修改 API 地址，编辑 `frontend/src/api/index.js` 中的 `baseURL`。

### 步骤 4: 启动服务

#### 方式一：本地启动

**启动后端**:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端**:

```bash
cd frontend
npm run dev
```

访问地址：
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000/docs

#### 方式二：Docker 部署

```bash
# 在项目根目录
docker-compose up --build -d
```

访问地址：
- 前端: http://localhost
- 后端 API: http://localhost:8000/docs

**查看日志**:

```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

**停止服务**:

```bash
docker-compose down
```

---

## 快速开始

### 基本使用流程

1. **上传文档**
   - 打开前端界面
   - 点击上传区域，选择 PPTX 或 PDF 文件
   - 或输入文档 URL

2. **等待解析**
   - 系统自动解析文档
   - 显示解析后的幻灯片列表

3. **执行全局分析**（可选，建议执行）
   - 点击"全局分析"按钮
   - 等待分析完成
   - 查看文档主题和知识点框架

4. **单页分析**
   - 选择要分析的页面
   - 点击"使用 AI 深度分析此页面"
   - 实时查看分析进度
   - 查看分析结果（学习笔记、知识缺口、补充说明等）

### 使用示例

#### 示例 1: 通过 Web 界面使用

1. 访问前端地址（http://localhost:5173 或 http://localhost）
2. 上传 PPT 文件
3. 等待解析完成
4. 点击"全局分析"按钮（可选）
5. 选择页面，点击"使用 AI 深度分析此页面"
6. 查看分析结果

#### 示例 2: 通过 API 使用

**步骤 1: 上传文档**

```bash
curl -X POST "http://localhost:8000/api/v1/expand-ppt" \
  -F "file=@presentation.pptx"
```

**响应**:

```json
{
  "doc_id": "abc123-def456-...",
  "file_hash": "sha256-hash",
  "slides": [
    {
      "title": "第1页",
      "raw_content": "内容...",
      "raw_points": []
    }
  ]
}
```

**步骤 2: 全局分析**

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-document-global" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "abc123-def456-...",
    "force": false
  }'
```

**步骤 3: 单页分析**

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-page" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "abc123-def456-...",
    "page_id": 1,
    "title": "第1页标题",
    "content": "第1页内容",
    "raw_points": [],
    "force": false
  }'
```

---

## 功能详解

### 全局分析功能

#### 功能说明

全局分析功能分析整个文档的主题、章节结构和知识点框架，为单页分析提供上下文信息。

#### 使用方式

**Web 界面**:
1. 上传文档后，点击"全局分析"按钮
2. 等待分析完成
3. 查看文档主题和知识点单元

**API 调用**:

```bash
POST /api/v1/analyze-document-global
Content-Type: application/json

{
  "doc_id": "your-doc-id",
  "force": false
}
```

#### 输出内容

- **主题**: 文档的核心主题
- **章节结构**: 文档的主要章节及其包含的页面
- **知识逻辑流程**: 章节之间的知识逻辑关系
- **知识点单元**: 跨页面的知识点单元列表

#### 缓存机制

- 全局分析结果会自动保存到数据库
- 如果文档已有全局分析结果，直接返回缓存（除非 `force=true`）
- 使用 `force=true` 可以强制重新分析

### 单页分析功能

#### 功能说明

单页分析功能对单个页面进行深度分析，包括：
- 知识聚类：识别难以理解的概念
- 理解笔记生成：生成结构化学习笔记
- 知识缺口识别：识别学生理解障碍点
- 知识扩展：为缺口生成补充说明
- 外部检索：从网络检索参考资料
- 一致性校验：校验扩展内容的准确性

#### 使用方式

**Web 界面**:
1. 选择要分析的页面
2. 点击"使用 AI 深度分析此页面"
3. 实时查看分析进度（知识聚类 → 学习笔记 → 知识缺口 → 补充说明 → 参考资料）
4. 查看最终分析结果

**API 调用**:

**非流式分析**:

```bash
POST /api/v1/analyze-page
Content-Type: application/json

{
  "doc_id": "your-doc-id",
  "page_id": 1,
  "title": "页面标题",
  "content": "页面内容",
  "raw_points": [],
  "force": false
}
```

**流式分析**（推荐）:

```bash
POST /api/v1/analyze-page-stream
Content-Type: application/json

{
  "doc_id": "your-doc-id",
  "page_id": 1,
  "title": "页面标题",
  "content": "页面内容",
  "raw_points": [],
  "force": false
}
```

#### 输出内容

- **知识聚类**: 难以理解的概念列表，包含难度级别和原因说明
- **理解笔记**: Markdown 格式的结构化学习笔记
- **知识缺口**: 识别的知识缺口列表，包含缺口类型和优先级
- **补充说明**: 为知识缺口生成的补充说明内容
- **参考资料**: 从外部知识源检索的参考资料

#### 流式分析

流式分析使用 Server-Sent Events (SSE) 协议，实时返回各阶段的分析结果：

- `stage: 'clustering'`: 知识聚类结果
- `stage: 'understanding'`: 理解笔记
- `stage: 'gaps'`: 知识缺口
- `stage: 'expansion'`: 扩展内容
- `stage: 'retrieval'`: 参考资料
- `stage: 'complete'`: 分析完成

#### 全局上下文支持

单页分析可以基于全局分析结果进行，提供更准确的上下文：

- 如果文档有全局分析结果，会自动加载并传递给各个 Agent
- Agent 会参考全局知识点框架，提供更准确的分析
- 建议先执行全局分析，再执行单页分析

### 数据持久化

#### 数据库位置

- **路径**: `backend/pptas_cache.sqlite3`
- **服务类**: `src/services/persistence_service.py` - `PersistenceService`

#### 存储内容

- **documents 表**: 存储文档基本信息和全局分析结果
- **page_analysis 表**: 存储单页分析结果

#### 缓存机制

- 全局分析结果缓存在 `documents.global_analysis_json` 字段
- 单页分析结果缓存在 `page_analysis.analysis_json` 字段
- 如果已有分析结果，直接返回缓存（除非 `force=true`）

---

## API 接口文档

### 文档上传接口

#### POST /api/v1/expand-ppt

上传并解析 PPT/PDF 文档。

**请求方式**: `multipart/form-data` 或 `application/json`

**参数**:
- `file` (File, 可选): PPT/PDF 文件
- `url` (string, 可选): 文档 URL

**响应**:

```json
{
  "doc_id": "abc123-def456-...",
  "file_hash": "sha256-hash",
  "slides": [
    {
      "title": "第1页",
      "raw_content": "内容...",
      "raw_points": []
    }
  ]
}
```

**示例**:

```bash
# 文件上传
curl -X POST "http://localhost:8000/api/v1/expand-ppt" \
  -F "file=@presentation.pptx"

# URL 上传
curl -X POST "http://localhost:8000/api/v1/expand-ppt" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/presentation.pptx"}'
```

### 全局分析接口

#### POST /api/v1/analyze-document-global

对整个文档进行全局分析。

**请求体**:

```json
{
  "doc_id": "your-doc-id",
  "force": false
}
```

**参数说明**:
- `doc_id` (string, 必需): 文档ID
- `force` (boolean, 可选): 是否强制重新分析，忽略缓存（默认: false）

**响应**:

```json
{
  "success": true,
  "doc_id": "your-doc-id",
  "global_analysis": {
    "main_topic": "文档主题",
    "chapters": [
      {
        "title": "章节标题",
        "pages": [1, 2, 3],
        "key_concepts": ["概念1", "概念2"]
      }
    ],
    "knowledge_flow": "知识逻辑流程描述",
    "knowledge_units": [
      {
        "unit_id": "unit_1",
        "title": "知识点单元标题",
        "pages": [1, 2],
        "core_concepts": ["核心概念1", "核心概念2"]
      }
    ],
    "total_pages": 10
  },
  "cached": false
}
```

### 单页分析接口

#### POST /api/v1/analyze-page

对单个页面进行深度分析（非流式）。

**请求体**:

```json
{
  "doc_id": "your-doc-id",
  "page_id": 1,
  "title": "页面标题",
  "content": "页面内容",
  "raw_points": [],
  "force": false
}
```

**参数说明**:
- `doc_id` (string, 可选): 文档ID，用于缓存
- `page_id` (integer, 必需): 页面编号（从1开始）
- `title` (string, 必需): 页面标题
- `content` (string, 必需): 页面内容
- `raw_points` (array, 可选): 原始要点列表
- `force` (boolean, 可选): 是否强制重新分析（默认: false）

**响应**:

```json
{
  "success": true,
  "cached": false,
  "data": {
    "page_id": 1,
    "title": "页面标题",
    "raw_content": "原始内容",
    "page_structure": {
      "page_id": 1,
      "title": "页面标题",
      "main_concepts": ["概念1", "概念2"],
      "key_points": ["要点1", "要点2"]
    },
    "knowledge_clusters": [
      {
        "concept": "概念名称",
        "difficulty_level": 3,
        "why_difficult": "为什么难理解",
        "related_concepts": ["相关概念"]
      }
    ],
    "understanding_notes": "Markdown 格式的学习笔记",
    "knowledge_gaps": [
      {
        "concept": "需要补充的概念",
        "gap_types": ["直观解释"],
        "priority": 4
      }
    ],
    "expanded_content": [
      {
        "concept": "概念",
        "gap_type": "直观解释",
        "content": "补充说明内容",
        "sources": ["来源1", "来源2"]
      }
    ],
    "references": [
      {
        "title": "参考资料标题",
        "url": "https://example.com",
        "source": "wikipedia",
        "snippet": "内容摘要"
      }
    ]
  }
}
```

#### POST /api/v1/analyze-page-stream

对单个页面进行流式深度分析。

**请求体**: 同 `/api/v1/analyze-page`

**响应**: Server-Sent Events (SSE) 流

**事件格式**:

```
data: {"stage": "clustering", "data": [...], "message": "正在分析难点概念..."}

data: {"stage": "understanding", "data": "...", "message": "正在生成学习笔记..."}

data: {"stage": "gaps", "data": [...], "message": "正在识别知识缺口..."}

data: {"stage": "expansion", "data": [...], "message": "正在生成补充说明..."}

data: {"stage": "retrieval", "data": [...], "message": "正在检索参考资料..."}

data: {"stage": "complete", "data": {...}, "message": "分析完成"}
```

**JavaScript 示例**:

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/analyze-page-stream',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      doc_id: "your-doc-id",
      page_id: 1,
      title: "页面标题",
      content: "页面内容",
      raw_points: [],
      force: false
    })
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`阶段: ${data.stage}, 消息: ${data.message}`);
  console.log('数据:', data.data);
};
```

### 查询接口

#### GET /api/v1/page-analysis

获取单页历史分析结果。

**查询参数**:
- `doc_id` (string, 必需): 文档ID
- `page_id` (integer, 必需): 页面编号

**响应**:

```json
{
  "success": true,
  "data": {
    "page_id": 1,
    "title": "页面标题",
    "understanding_notes": "...",
    "knowledge_gaps": [...],
    "_meta": {
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  }
}
```

#### GET /api/v1/page-analysis/all

获取文档所有已保存的页分析。

**查询参数**:
- `doc_id` (string, 必需): 文档ID

**响应**:

```json
{
  "success": true,
  "data": {
    "1": {
      "page_id": 1,
      "title": "第1页",
      ...
    },
    "2": {
      "page_id": 2,
      "title": "第2页",
      ...
    }
  }
}
```

### 其他接口

#### GET /api/v1/health

健康检查接口。

**响应**:

```json
{
  "status": "ok",
  "version": "0.2.0"
}
```

#### GET /api/v1/health/complete

完整的系统健康检查（包括后端和 LLM）。

**响应**:

```json
{
  "backend": {
    "status": "ok",
    "version": "0.2.0"
  },
  "llm": {
    "status": "ok",
    "model": "gpt-4",
    "response_preview": "就绪"
  }
}
```

---

## 配置说明

### 配置文件位置

- **主配置文件**: `backend/config.json`
- **配置管理类**: `src/config.py` - `ConfigManager`

### 配置结构详解

#### LLM 配置

```json
{
  "llm": {
    "api_key": "your-api-key",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
  }
}
```

**配置项说明**:
- `api_key`: LLM API 密钥（必需）
- `base_url`: LLM API 基础 URL（必需）
- `model`: 使用的模型名称（必需）

**支持的提供商示例**:

- OpenAI: `"base_url": "https://api.openai.com/v1"`, `"model": "gpt-4"`
- SiliconFlow: `"base_url": "https://api.siliconflow.cn/v1"`, `"model": "deepseek-ai/DeepSeek-V3.2-Exp"`
- 其他 OpenAI 兼容接口

#### 检索配置

```json
{
  "retrieval": {
    "preferred_sources": ["arxiv", "wikipedia", "baidu_baike"],
    "max_results": 5,
    "local_rag_priority": true
  }
}
```

**配置项说明**:
- `preferred_sources`: 优先使用的知识源列表，可选值: `["arxiv", "wikipedia", "baidu_baike"]`
- `max_results`: 每个知识源的最大结果数
- `local_rag_priority`: 是否优先使用本地 RAG

#### 扩展配置

```json
{
  "expansion": {
    "max_revisions": 3,
    "min_gap_priority": 2,
    "temperature": 0.5
  }
}
```

**配置项说明**:
- `max_revisions`: 最大修订次数（一致性校验失败时）
- `min_gap_priority`: 最小缺口优先级（低于此优先级的缺口会被忽略）
- `temperature`: LLM 温度参数（0-1，越高越有创意）

#### 流式配置

```json
{
  "streaming": {
    "enabled": true,
    "chunk_size": 100
  }
}
```

**配置项说明**:
- `enabled`: 是否启用流式输出
- `chunk_size`: 流式输出的块大小

#### 知识库配置

```json
{
  "knowledge_base": {
    "path": "./knowledge_base",
    "chunk_size": 1500,
    "chunk_overlap": 300
  }
}
```

**配置项说明**:
- `path`: 本地知识库路径
- `chunk_size`: 文档分块大小
- `chunk_overlap`: 分块重叠大小

#### 向量存储配置

```json
{
  "vector_store": {
    "path": "./ppt_vector_db",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "embedding_model": "BAAI/bge-m3"
  }
}
```

**配置项说明**:
- `path`: 向量数据库路径
- `chunk_size`: 向量化分块大小
- `chunk_overlap`: 分块重叠大小
- `embedding_model`: 嵌入模型名称

### 配置加载优先级

1. 环境变量（最高优先级）
2. `config.json` 文件
3. 默认值（最低优先级）

---

## 数据管理

### 数据库位置

- **路径**: `backend/pptas_cache.sqlite3`
- **服务类**: `src/services/persistence_service.py` - `PersistenceService`

### 数据库结构

#### documents 表

存储文档基本信息和分析结果。

**字段说明**:
- `doc_id`: 文档唯一标识（UUID）
- `file_name`: 原始文件名
- `file_type`: 文件类型（pptx/pdf）
- `file_hash`: 文件内容的 SHA256 哈希值
- `slides_json`: 解析后的 slides 数据（JSON 字符串）
- `global_analysis_json`: 全局分析结果（JSON 字符串）
- `created_at`: 文档创建时间
- `updated_at`: 文档最后更新时间

#### page_analysis 表

存储单页分析结果。

**字段说明**:
- `doc_id`: 文档ID（外键）
- `page_id`: 页面编号（从1开始）
- `analysis_json`: 单页分析结果（JSON 字符串）
- `created_at`: 分析结果创建时间
- `updated_at`: 分析结果最后更新时间

### 数据操作

#### 查询文档

```python
from src.services.persistence_service import PersistenceService

persistence = PersistenceService("backend/pptas_cache.sqlite3")

# 通过 doc_id 查询
doc = persistence.get_document_by_id("doc-123")

# 通过 file_hash 查询
doc = persistence.get_document_by_hash("abc123...")

# 获取文档的全局分析
if doc and doc.get("global_analysis"):
    global_analysis = doc["global_analysis"]
```

#### 查询单页分析

```python
# 获取单个页面的分析
analysis = persistence.get_page_analysis("doc-123", 1)

# 获取文档所有页面的分析
all_analyses = persistence.list_page_analyses("doc-123")
# 返回: {1: {...}, 2: {...}, ...}
```

#### 使用 SQLite 命令行查询

```bash
# 打开数据库
sqlite3 backend/pptas_cache.sqlite3

# 查看所有文档
SELECT doc_id, file_name, file_type, created_at FROM documents;

# 查看文档的全局分析
SELECT doc_id, json_extract(global_analysis_json, '$.main_topic') as main_topic 
FROM documents 
WHERE global_analysis_json IS NOT NULL;

# 查看某个文档的所有页面分析
SELECT page_id, json_extract(analysis_json, '$.title') as title 
FROM page_analysis 
WHERE doc_id = 'your-doc-id';

# 查看分析结果的数量
SELECT COUNT(*) FROM page_analysis WHERE doc_id = 'your-doc-id';
```

### 数据备份

建议定期备份数据库文件：

```bash
# 备份数据库
cp backend/pptas_cache.sqlite3 backend/pptas_cache.sqlite3.backup

# 恢复数据库
cp backend/pptas_cache.sqlite3.backup backend/pptas_cache.sqlite3
```

---

## 故障排除

### 常见问题

#### Q1: 后端启动失败

**问题**: 启动后端时出现错误

**解决方案**:
1. 检查 Python 版本是否为 3.9+
2. 检查是否安装了所有依赖: `pip install -r requirements.txt`
3. 检查配置文件 `config.json` 是否存在且格式正确
4. 检查端口 8000 是否被占用

#### Q2: LLM 调用失败

**问题**: API 调用返回错误

**解决方案**:
1. 检查 `config.json` 中的 `api_key` 是否正确
2. 检查 `base_url` 是否可访问
3. 检查网络连接
4. 检查 API 配额是否充足

#### Q3: 前端无法连接后端

**问题**: 前端无法访问后端 API

**解决方案**:
1. 检查后端是否正常运行
2. 检查前端配置中的 API 地址是否正确
3. 检查 CORS 配置
4. 检查防火墙设置

#### Q4: 分析结果为空或不准确

**问题**: 分析结果不理想

**解决方案**:
1. 检查文档内容是否足够（至少有几页内容）
2. 尝试执行全局分析，再执行单页分析
3. 检查 LLM 模型是否适合当前任务
4. 尝试调整配置参数（如 `temperature`）

#### Q5: 数据库文件损坏

**问题**: 数据库操作失败

**解决方案**:
1. 停止服务
2. 备份当前数据库文件
3. 删除损坏的数据库文件
4. 重启服务，系统会自动创建新的数据库

#### Q6: 外部检索失败

**问题**: 无法检索到参考资料

**解决方案**:
1. 检查网络连接
2. 检查外部知识源是否可访问（Wikipedia、Arxiv 等）
3. 系统会在检索前自动检查连接，如果所有源不可用，会跳过外部检索
4. 可以检查后端日志查看具体错误信息

### 调试技巧

#### 查看后端日志

后端日志会输出到控制台，包含：
- Agent 执行开始和结束
- LLM 调用信息
- 缓存命中情况
- 错误堆栈信息

#### 查看前端日志

打开浏览器开发者工具（F12），查看 Console 标签页，包含：
- API 请求和响应
- 分析进度信息
- 错误信息

#### 检查数据库

使用 SQLite 命令行工具检查数据库：

```bash
sqlite3 backend/pptas_cache.sqlite3

# 查看表结构
.schema documents
.schema page_analysis

# 查看数据
SELECT * FROM documents;
SELECT * FROM page_analysis;
```

---

## 高级用法

### 批量分析

#### Python 脚本示例

```python
import requests
import json

BASE_URL = "http://localhost:8000"
DOC_FILE = "presentation.pptx"

# 步骤1: 上传文档
print("步骤1: 上传文档...")
with open(DOC_FILE, "rb") as f:
    response = requests.post(
        f"{BASE_URL}/api/v1/expand-ppt",
        files={"file": f}
    )
doc_data = response.json()
doc_id = doc_data["doc_id"]
print(f"文档ID: {doc_id}")

# 步骤2: 全局分析
print("\n步骤2: 执行全局分析...")
response = requests.post(
    f"{BASE_URL}/api/v1/analyze-document-global",
    json={"doc_id": doc_id, "force": False}
)
global_analysis = response.json()["global_analysis"]
print(f"主题: {global_analysis['main_topic']}")
print(f"知识点单元数: {len(global_analysis['knowledge_units'])}")

# 步骤3: 批量单页分析
print("\n步骤3: 执行单页分析...")
slides = doc_data["slides"]
for i, slide in enumerate(slides, 1):
    print(f"\n分析第 {i} 页...")
    response = requests.post(
        f"{BASE_URL}/api/v1/analyze-page",
        json={
            "doc_id": doc_id,
            "page_id": i,
            "title": slide.get("title", ""),
            "content": slide.get("raw_content", ""),
            "raw_points": slide.get("raw_points", []),
            "force": False
        }
    )
    result = response.json()["data"]
    print(f"  理解笔记长度: {len(result['understanding_notes'])}")
    print(f"  知识缺口数: {len(result['knowledge_gaps'])}")
    print(f"  扩展内容数: {len(result['expanded_content'])}")

print("\n完成！")
```

### 自定义 Agent 行为

#### 修改 Prompt

编辑 `backend/src/agents/base.py` 中对应 Agent 的 prompt：

```python
class GapIdentificationAgent:
    def run(self, state: GraphState) -> GraphState:
        template = """你的自定义 prompt...
        
        {raw_text}
        
        ...
        """
        # ...
```

#### 调整参数

修改 Agent 的初始化参数：

```python
# 修改温度参数
self.llm = llm_config.create_llm(temperature=0.3)  # 改为 0.3

# 修改输入限制
content = state["raw_text"][:1500]  # 改为 1500
```

### 添加新的知识源

#### 实现新的 MCP 类

在 `backend/src/services/mcp_tools.py` 中添加：

```python
class NewSourceMCP:
    def search(self, query: str) -> List[Document]:
        # 实现搜索逻辑
        pass
```

#### 注册到 MCPRouter

```python
class MCPRouter:
    def __init__(self):
        self.sources = {
            "new_source": NewSourceMCP(),
            # ...
        }
```

### 性能调优

#### 减少 Token 消耗

1. 调整输入限制: 减少各 Agent 的输入文本长度
2. 使用更小的模型: 对于简单任务使用较小的模型
3. 启用缓存: 避免重复分析相同内容

#### 提高响应速度

1. 使用流式分析: 提前显示部分结果
2. 启用缓存: 避免重复分析
3. 优化网络: 使用更快的 LLM API
4. 减少检索结果: 降低 `retrieval.max_results` 的值

---

## 总结

本文档详细说明了 PPTAS 系统的使用方法，包括环境准备、安装配置、功能使用、API 接口、配置说明、数据管理和故障排除等。通过遵循本文档，您可以：

1. 成功部署和运行系统
2. 使用各种功能进行文档分析
3. 通过 API 集成到其他系统
4. 自定义和扩展系统功能
5. 解决常见问题

如有其他问题，请参考故障排除部分或查看源代码注释。
