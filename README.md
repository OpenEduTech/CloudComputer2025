## 📖 项目简介

FactGuardian 是一个基于大语言模型（LLM）的智能文档审核系统，能够自动从文档中提取关键事实，检测内部逻辑冲突，并通过外部验证来验证事实来源。系统特别适用于多人员协作文档的质量控制，如学术论文、可行性报告、技术文档等。

### 核心能力

- 🔍 **智能事实提取**：基于 LLM 的结构化事实提取，支持多种事实类型
- ⚔️ **冲突检测**：自动检测文档内部的数据不一致、逻辑矛盾、时间冲突
- ✅ **来源验证**：通过网络搜索和权威来源进行外部事实验证
- 📊 **参考对比**：跨文档相似性分析和引用关系检测
- 🖼️ **图文对比**：验证文本描述与视觉图表的一致性
- 🚀 **高性能**：批量并行处理，支持大规模文档分析

---

## ✨ 功能特性

### 核心功能

#### 1. 文档解析与事实提取
- **多格式支持**：DOCX、PDF、TXT、Markdown
- **结构化提取**：自动提取数据、日期、人名、结论、事件等事实
- **可验证性分类**：区分公开可验证事实和内部数据
- **位置追踪**：记录每个事实在文档中的位置

#### 2. 冲突检测
- **智能比对**：基于结构化字段的事实对生成
- **多类型检测**：
  - 数据不一致（数值冲突、百分比差异）
  - 逻辑矛盾（肯定/否定冲突）
  - 时间冲突（时间范围重叠或矛盾）
- **重复检测**：识别高频重复段落（出现3次以上）
- **批量处理**：并行 LLM 调用（batch_size=10），提升性能

#### 3. 事实验证
- **外部搜索**：集成 Tavily、Serper 等搜索 API，支持降级策略
- **LLM 评估**：使用思维链（Chain of Thought）分析
- **置信度评分**：High/Medium/Low 三级置信度
- **修正建议**：提供错误事实的修正建议

#### 4. 扩展功能

**参考文档对比**
- 多文档上传（主文档 + 多个参考文档）
- 段落级相似度计算（0-100%）
- 相似类型识别（直接引用/改写/思想借鉴/无关）
- 引用建议生成（needs_citation）

**图文一致性对比**
- 多 Vision API 支持（Claude / GPT-4V / 豆包）
- 架构图、流程图识别
- 核心逻辑与视觉细节区分
- 一致性评分和矛盾检测

---

## 🚀 快速开始

### 前置要求

- **操作系统**：Windows 10/11、macOS 10.15+ 或 Linux（Ubuntu 18.04+）
- **Docker Desktop**：版本 24.0.0 或更高
- **Docker Compose**：版本 1.29.0 或更高
- **内存**：8GB RAM 最低要求，16GB 推荐
- **存储**：5GB 可用磁盘空间
- **网络**：互联网连接用于外部事实验证

### 安装步骤

#### 1. 克隆仓库

```bash
git clone <repository-url>
cd factguardian
```

#### 2. 配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```env
# LLM API（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Redis 配置（可选，默认使用 Docker Compose 中的 Redis）
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Vision API（可选，用于图片提取功能）
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DOUBAO_API_KEY=your_doubao_api_key_here
DOUBAO_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3

# 搜索 API（可选，用于事实验证）
TAVILY_API_KEY=your_tavily_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

#### 3. 启动服务

**Windows（PowerShell）：**
```powershell
.\start-docker.ps1
```

**Linux/macOS：**
```bash
docker-compose up -d --build
```

#### 4. 验证安装

访问以下地址验证服务是否正常：

- **前端界面**：http://localhost:3000
- **后端 API 文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/health

---

## 📚 使用指南

### Web 界面使用

1. **上传文档**
   - 访问 http://localhost:3000
   - 点击上传按钮，选择文档文件（支持 DOCX、PDF、TXT、MD）
   - 等待文档解析完成

2. **提取事实**
   - 点击"提取事实"按钮
   - 系统自动提取文档中的关键事实
   - 查看提取的事实列表和统计信息

3. **检测冲突**
   - 点击"检测冲突"按钮
   - 系统自动比对事实，识别冲突
   - 在文档中高亮显示冲突位置

4. **验证事实**
   - 点击"验证事实"按钮
   - 系统通过网络搜索验证事实真实性
   - 查看验证结果和置信度评分

### API 使用示例

#### 1. 文档上传

```bash
curl -X POST "http://localhost:8000/api/upload" \
     -F "file=@document.docx"
```

响应：
```json
{
  "success": true,
  "document_id": "abc12345",
  "filename": "document.docx",
  "word_count": 5000,
  "section_count": 10,
  "sections": [...]
}
```

#### 2. 提取事实

方式一：直接上传并提取（一步到位）
```bash
curl -X POST "http://localhost:8000/api/extract-facts" \
     -F "file=@document.docx"
```

方式二：使用已上传的文档ID（推荐，可复用已解析文档）
```bash
# 先上传获取 document_id
curl -X POST "http://localhost:8000/api/upload" -F "file=@document.docx"

# 然后使用返回的 document_id 提取事实
curl -X POST "http://localhost:8000/api/documents/abc12345/extract-facts"
```

#### 3. 检测冲突

```bash
curl -X POST "http://localhost:8000/api/detect-conflicts/abc12345"
```

#### 4. 验证事实

```bash
curl -X POST "http://localhost:8000/api/documents/abc12345/verify-facts"
```

#### 5. 参考文档对比

```bash
curl -X POST "http://localhost:8000/api/compare-references" \
     -H "Content-Type: application/json" \
     -d '{
       "main_doc_id": "main123",
       "ref_doc_ids": ["ref1", "ref2"],
       "similarity_threshold": 0.3
     }'
```

#### 6. 图文对比

```bash
curl -X POST "http://localhost:8000/api/compare-image-text" \
     -F "file=@architecture.png" \
     -F "document_id=abc12345"
```

#### 7. 实时进度（SSE）

```javascript
const eventSource = new EventSource('http://localhost:8000/api/progress/abc12345');
eventSource.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log('进度更新:', progress);
};
```

---

## 🏗️ 项目结构

```
factguardian/
├── backend/                          # 后端服务
│   ├── app/
│   │   ├── main.py                  # FastAPI 应用入口点（1067行）
│   │   └── services/                 # 业务逻辑服务层
│   │       ├── __init__.py          # 服务模块初始化
│   │       ├── parser.py            # 文档解析服务（DOCX/PDF/TXT/MD）
│   │       ├── llm_client.py        # LLM API 客户端（DeepSeek 封装，292行）
│   │       ├── redis_client.py      # Redis 缓存客户端（单例模式，内存降级）
│   │       ├── fact_extractor.py    # 事实提取服务（结构化提取）
│   │       ├── fact_schema.py       # 事实数据模型定义
│   │       ├── fact_normalizer.py   # 事实规范化服务
│   │       ├── conflict_detector.py # 冲突检测服务（734行，批量并行处理）
│   │       ├── verifier.py          # 事实验证服务（272行，外部搜索+LLM）
│   │       ├── lsh_filter.py        # LSH 相似度过滤（MinHash 算法）
│   │       ├── search_client.py     # 外部搜索客户端（Tavily/Serper/Mock）
│   │       ├── prompt_tuner.py      # Prompt 优化器（材料驱动提示）
│   │       ├── reference_comparator.py # 参考文档对比服务（229行）
│   │       ├── image_extractor.py   # 图片内容提取（405行，多 Vision API）
│   │       ├── image_text_comparator.py # 图文一致性对比服务（223行）
│   │       ├── coref_resolver.py    # 共指消解服务
│   │       ├── nlp_extractor.py     # NLP 提取服务
│   │       ├── semantic_indexer.py  # 语义索引服务
│   │       └── progress_manager.py  # 进度管理器（SSE 进度推送）
│   ├── Dockerfile                   # 后端容器定义（Python 3.10-slim）
│   ├── .dockerignore                # Docker 构建忽略文件
│   ├── requirements.txt             # Python 依赖包列表
│   ├── test_auto.py                 # 自动化测试脚本
│   ├── test_image_comparison.py     # 图文对比测试脚本
│   ├── test_reference_comparison.py # 参考对比测试脚本
│   └── [测试数据文件]                # test_data*.txt, *.docx, *.png 等
│
├── frontend/                         # 前端应用
│   ├── src/
│   │   ├── main.jsx                 # React 应用入口点
│   │   ├── App.jsx                  # 主应用组件（路由和状态管理）
│   │   ├── api.js                   # API 调用封装（axios 封装）
│   │   ├── index.css                # 全局样式文件
│   │   └── components/               # UI 组件目录
│   │       ├── UploadSection.jsx    # 文件上传组件
│   │       ├── DocumentViewer.jsx   # 文档浏览组件（支持高亮和跳转）
│   │       ├── ConflictList.jsx      # 冲突列表组件（显示冲突详情）
│   │       ├── RepetitionList.jsx    # 重复内容列表组件
│   │       ├── VerificationResult.jsx # 校验结果组件（显示验证结果）
│   │       ├── FunLoading.jsx       # 加载动画组件（SSE 进度显示）
│   │       ├── MultiDocComparison.jsx # 多文档对比组件（参考对比功能）
│   │       └── ImageTextComparison.jsx # 图文对比组件
│   ├── public/                       # 静态资源目录
│   ├── Dockerfile                   # 前端容器定义（多阶段构建）
│   ├── .dockerignore                # Docker 构建忽略文件
│   ├── package.json                  # Node.js 依赖配置
│   ├── package-lock.json             # 依赖锁定文件
│   ├── vite.config.js                # Vite 构建配置
│   ├── tailwind.config.js            # Tailwind CSS 配置
│   ├── postcss.config.js             # PostCSS 配置
│   └── index.html                    # HTML 入口文件
│
├── image/                            # 图片资源目录（示例图片等）
│
├── .vscode/                          # VS Code 配置目录
│
├── docker-compose.yml                # Docker Compose 开发环境配置
├── docker-compose.prod.yml           # Docker Compose 生产环境配置（如已创建）
├── start-docker.ps1                  # Windows PowerShell 启动脚本
├── stop-docker.ps1                   # Windows PowerShell 停止脚本
├── restart-docker.ps1                # Windows PowerShell 重启脚本
│
├── .env                              # 环境变量配置（需自行创建）
├── .env.example                      # 环境变量模板
├── .gitignore                        # Git 忽略文件配置
│
├── README.md                         # 项目说明文档（本文件）
├── FRONTEND_GUIDE.md                 # 前端开发指南
├── PROGRESS.md                       # 开发进度文档
├── EXPERIMENT_REPORT.md              # 实验报告文档
├── TODO.md                           # 待办事项列表
├── 分工.md                            # 项目分工文档
└── ZXY_BRANCH_REVIEW.md             # 分支审查文档
```

---

## 🔧 开发指南

### 本地开发环境

#### 后端开发

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev
```

### 代码规范

- **Python**：遵循 PEP 8，使用类型提示（Type Hints）
- **JavaScript**：使用 ES6+ 语法，遵循 ESLint 规则
- **提交信息**：使用约定式提交格式 `[类型] 简短描述`
  - 类型：`feat`（新功能）、`fix`（修复）、`refactor`（重构）、`docs`（文档）

### 调试

```bash
# 查看服务日志
docker-compose logs backend
docker-compose logs frontend

# 实时跟踪日志
docker-compose logs -f backend

# 访问容器 shell
docker-compose exec backend bash
docker-compose exec frontend sh

# 测试 API 端点
curl http://localhost:8000/health
```

### 添加依赖

**后端：**
1. 更新 `backend/requirements.txt`
2. 重新构建 Docker 镜像：
   ```bash
   docker-compose build backend
   ```
3. 重启服务：
   ```bash
   docker-compose restart backend
   ```

**前端：**
1. 更新 `frontend/package.json`
2. 重新构建 Docker 镜像：
   ```bash
   docker-compose build frontend
   ```
3. 重启服务：
   ```bash
   docker-compose restart frontend
   ```

### 测试

```bash
# 后端测试
cd backend
python test_auto.py test_data_simple.txt

# 图文对比测试
python test_auto.py document.docx image-compare architecture.png

# 参考对比测试
python test_auto.py main.docx ref-compare reference1.docx
```

---

## 📡 API 文档

### 核心端点

| 端点                                         | 方法 | 描述                           |
| -------------------------------------------- | ---- | ------------------------------ |
| `/`                                          | GET  | API 信息                       |
| `/health`                                    | GET  | 服务健康检查                   |
| `/api/upload`                                | POST | 上传并解析文档                 |
| `/api/extract-facts`                         | POST | 从文档提取事实                 |
| `/api/documents/{document_id}/extract-facts` | POST | 根据文档ID提取事实             |
| `/api/facts/{document_id}`                   | GET  | 检索文档事实                   |
| `/api/detect-conflicts/{document_id}`        | POST | 检测文档冲突                   |
| `/api/conflicts/{document_id}`               | GET  | 检索文档冲突                   |
| `/api/documents/{document_id}/verify-facts`  | POST | 验证文档事实                   |
| `/api/analyze`                               | POST | 完整分析流程（上传→提取→检测） |
| `/api/upload-multiple`                       | POST | 多文件上传（主文档+参考文档）  |
| `/api/compare-references`                    | POST | 对比参考文档                   |
| `/api/extract-from-image`                    | POST | 提取图片内容                   |
| `/api/compare-image-text`                    | POST | 对比图片与文本一致性           |
| `/api/progress/{document_id}`                | GET  | SSE 进度推送                   |
| `/api/progress-status/{document_id}`         | GET  | 获取进度状态（轮询方式）       |

完整的交互式 API 文档请访问：http://localhost:8000/docs

---

## 🐳 Docker 部署

### 开发环境

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 停止服务
docker-compose down
```

### 生产环境

```bash
# 使用生产环境配置（如已创建）
docker-compose -f docker-compose.prod.yml up -d --build

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 服务管理脚本（Windows）

```powershell
# 启动服务
.\start-docker.ps1

# 停止服务
.\stop-docker.ps1

# 重启服务
.\restart-docker.ps1
```

---

## 🔍 技术架构

### 系统架构图

```
┌─────────────┐
│   Frontend  │  React + Vite + Tailwind CSS
│  (Port 3000)│
└──────┬──────┘
       │ HTTP/SSE
┌──────▼──────┐
│   Backend   │  FastAPI + Python 3.10
│  (Port 8000)│
└──────┬──────┘
       │
   ┌───┴───┬──────────┬──────────┐
   │       │          │          │
┌──▼──┐ ┌─▼──┐  ┌────▼────┐ ┌───▼───┐
│Redis│ │LLM │  │ Search  │ │ Vision │
│Cache│ │API │  │  APIs   │ │  APIs  │
└─────┘ └────┘  └─────────┘ └────────┘
```

### 技术栈

**后端**
- Python 3.10+
- FastAPI 0.104+
- Uvicorn（ASGI 服务器）
- Redis（缓存，支持内存降级）
- DeepSeek API（LLM）
- Tavily/Serper（搜索 API，支持 Mock 降级）
- Claude/GPT-4V/豆包（Vision API）

**前端**
- React 18
- Vite 5
- Tailwind CSS 3
- Axios（HTTP 客户端）
- Server-Sent Events（实时进度推送）

**基础设施**
- Docker & Docker Compose
- Nginx（前端生产环境）
- Redis 7

---

## 📊 性能指标

- **事实提取**：平均 2-5 秒/章节（取决于章节长度和 LLM 响应时间）
- **冲突检测**：300 对事实约 15-20 秒（批量并行处理，batch_size=10）
- **事实验证**：单个事实约 3-5 秒（包含搜索和 LLM 评估）
- **参考对比**：100 个段落对比约 30 秒
- **图文对比**：单次对比约 10 秒（包含图片提取和文本对比）

---

## 🛠️ 故障排除

### 常见问题

#### 1. 服务无法启动

**问题**：Docker 容器无法启动

**解决方案**：
- 检查 Docker Desktop 是否正在运行
- 验证端口 8000、3000、6379 是否被占用
- 查看服务日志：`docker-compose logs backend`
- 检查 `.env` 文件是否存在且配置正确

#### 2. API 密钥错误

**问题**：LLM 功能不可用

**解决方案**：
- 确保 `.env` 文件存在并包含有效的 `DEEPSEEK_API_KEY`
- 检查 API 密钥格式和权限
- 验证与 DeepSeek 服务的网络连接
- 查看后端日志确认错误信息

#### 3. Redis 连接失败

**问题**：后端无法连接 Redis

**解决方案**：
- 检查 Redis 容器是否正常运行：`docker-compose ps redis`
- 验证 `REDIS_HOST` 环境变量（开发环境应为 `redis`）
- 查看 Redis 日志：`docker-compose logs redis`
- 系统会自动降级到内存存储，但会记录警告日志

#### 4. 前端路由 404

**问题**：刷新页面后出现 404

**解决方案**：
- 确保使用生产环境配置（Nginx 已配置 SPA 路由支持）
- 检查 Nginx 配置中的 `try_files` 设置
- 开发环境使用 Vite 开发服务器，无需特殊配置

#### 5. 内存不足

**问题**：处理大文档时内存溢出

**解决方案**：
- 增加 Docker Desktop 内存分配（最低 8GB，推荐 16GB）
- 关闭其他内存密集型应用程序
- 监控资源使用：`docker stats`
- 考虑分批处理大文档

#### 6. 文件上传失败

**问题**：文件上传被拒绝

**解决方案**：
- 检查文件大小限制（FastAPI 默认无限制，但建议 < 50MB）
- 验证支持的文件格式（DOCX、PDF、TXT、MD）
- 确保文件权限正确
- 查看后端日志获取详细错误信息

### 性能调优

- **Redis 配置**：调整 Redis 内存设置以适应大型文档（`maxmemory` 参数）
- **LLM 批量处理**：调整 `batch_size` 参数（默认 10）以优化 API 使用
- **冲突检测**：调整 `max_pairs` 参数（默认 300）平衡准确性和速度
- **前端优化**：生产环境使用 Nginx，启用 Gzip 压缩和静态资源缓存

---

## 📝 更新日志

### v1.0.0 (2025-01)

**核心功能**
- ✅ 文档解析（DOCX、PDF、TXT、MD）
- ✅ 事实提取（结构化提取，支持多种事实类型）
- ✅ 冲突检测（数据不一致、逻辑矛盾、时间冲突）
- ✅ 事实验证（外部搜索 + LLM 评估）
- ✅ 重复内容检测

**扩展功能**
- ✅ 参考文档对比
- ✅ 图文一致性对比

**性能优化**
- ✅ 批量并行处理
- ✅ Redis 缓存（支持内存降级）
- ✅ SSE 实时进度推送
- ✅ LSH 相似度过滤（可选）

**稳定性提升**
- ✅ 完善的错误处理和容错机制
- ✅ JSON 解析容错（多策略提取）
- ✅ 服务降级策略（Redis、搜索、Vision API）
- ✅ 健康检查端点

---

## 👥 项目成员

- **詹江叶煜** (10235501471) - 冲突监测功能实现
- **马舒童** (10235501462) - 冲突监测功能优化与前端页面搭建
- **张欣扬** (10235501413) - 扩展功能实现

详细分工请参考 [分工.md](分工.md)

---

## 📚 相关文档

- [实验报告](EXPERIMENT_REPORT.md) - 详细实验报告
- [待办事项](TODO.md) - 开发路线图
- [分工文档](分工.md) - 项目分工说明

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [React](https://react.dev/) - 用户界面库
- [DeepSeek](https://www.deepseek.com/) - 大语言模型服务
- [Redis](https://redis.io/) - 内存数据结构存储
- [Vite](https://vitejs.dev/) - 下一代前端构建工具
- [Tailwind CSS](https://tailwindcss.com/) - 实用优先的 CSS 框架

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
