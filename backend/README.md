# PPTAS 后端 - PPT 扩展系统

## 概述

这是 PPTAS (PPT 智能扩展系统) 的后端实现，集成了完整的 PPT 智能扩展功能。

- 🤖 基于 LangGraph 的多 Agent 协作架构
- 📚 支持多种知识源（维基百科、Arxiv、百度百科等）
- 🔍 智能知识缺口识别和内容扩展
- ✅ 自动一致性校验和内容优化

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置 API Key
编辑 `config.json`:
```json
{
  "llm": {
    "api_key": "your-openai-api-key",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
  }
}
```

或使用环境变量:
```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4"
```

### 3. 启动服务
```bash
python main.py
```

### 4. 访问 API
- 文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 核心 API

### 1. PPT 智能扩展
```bash
POST /api/v1/expand-slides
```

**参数**:
- `file` (可选): PPT/PDF 文件
- `url` (可选): 文件 URL

**示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/expand-slides" \
  -F "file=@presentation.pptx"
```

**返回**:
```json
{
  "original_slides": [...],
  "expanded_content": [
    {
      "page_id": 1,
      "page_structure": {...},
      "knowledge_gaps": [...],
      "expanded_content": [...],
      "final_notes": "..."
    }
  ]
}
```

### 2. PPT 解析（简单版）
```bash
POST /api/v1/expand-ppt
```

仅返回解析后的 PPT 结构，不进行扩展。

### 3. 健康检查
```bash
GET /api/v1/health
```

## 系统架构

```
FastAPI 应用层
    ↓
PPT 解析服务 (ppt_parser_service.py)
    ↓
PPT 扩展服务 (ppt_expansion_service.py)
    ↓
LangGraph 工作流
    ├─ GlobalStructureAgent (全局结构解析)
    ├─ KnowledgeClusteringAgent (知识点划分)
    ├─ StructureUnderstandingAgent (结构语义理解)
    ├─ GapIdentificationAgent (知识缺口识别)
    ├─ KnowledgeExpansionAgent (知识扩展)
    ├─ RetrievalAgent (检索增强)
    ├─ ConsistencyCheckAgent (一致性校验)
    └─ StructuredOrganizationAgent (内容整理)
    ↓
知识源工具 (mcp_tools.py)
    ├─ WikipediaMCP
    ├─ ArxivMCP
    ├─ GoogleScholarMCP
    └─ BaiduBaikeMCP
```

## 项目结构

```
backend/
├── src/
│   ├── agents/                      # Agent 层
│   │   ├── base.py                 # 8 个 Agent 实现
│   │   ├── models.py               # 数据模型
│   │   └── __init__.py
│   ├── services/                    # 服务层
│   │   ├── ppt_expansion_service.py # 核心服务
│   │   ├── ppt_parser_service.py   # PPT 解析
│   │   ├── mcp_tools.py            # 知识源工具
│   │   └── __init__.py
│   ├── utils/                       # 工具层
│   │   ├── helpers.py
│   │   └── __init__.py
│   └── app.py                       # FastAPI 应用
├── config.json                      # 配置文件
├── requirements.txt                 # 依赖
├── main.py                          # 启动脚本
├── verify_migration.py              # 验证脚本
├── MIGRATION_REPORT.md              # 迁移报告
├── MIGRATION_SUMMARY.md             # 详细文档
└── QUICKSTART.md                    # 快速指南
```

## 配置说明

### config.json

```json
{
  "llm": {
    "api_key": "sk-xxx",                    // LLM API Key
    "base_url": "https://api.openai.com/v1", // API 基础 URL
    "model": "gpt-4"                        // 模型名称
  },
  "retrieval": {
    "preferred_sources": ["arxiv", "wikipedia"], // 优先知识源
    "max_results": 3,                       // 最大结果数
    "local_rag_priority": true              // 本地 RAG 优先
  },
  "expansion": {
    "max_revisions": 2,                     // 最大修订次数
    "min_gap_priority": 3,                  // 最小缺口优先级
    "temperature": 0.7                      // LLM 温度
  }
}
```

## 核心功能

### 1. 全局结构解析
自动识别 PPT 的章节结构、层级关系和知识流程。

### 2. 知识点划分
跨页识别完整的知识单元，确保每个单元包含完整的教学闭环。

### 3. 知识缺口识别
自动识别缺少直观解释、公式推导、背景知识或应用场景的内容。

### 4. 定向知识扩展
基于识别的缺口，使用 LLM 生成高质量的扩展内容。

### 5. 外部检索增强
集成维基百科、Arxiv、百度百科等知识源，为扩展内容提供支撑。

### 6. 一致性校验
自动校验扩展内容是否与原始 PPT 一致，避免引入错误信息。

### 7. 内容结构化整理
将扩展内容整理为 Markdown 格式的学习笔记。

## 验证迁移

运行验证脚本确保所有文件就位:

```bash
python verify_migration.py
```

预期输出:
```
✅ 迁移验证通过！所有 11 项检查均已完成。
```

## 常见问题

### Q: 如何使用本地知识库？
A: 在 `knowledge_base/` 文件夹中放置文档，配置 `expansion.local_rag_priority: true`。

### Q: 如何切换 LLM 供应商？
A: 修改 `config.json` 中的 `llm.base_url` 和 `llm.model`。

### Q: 扩展流程需要多长时间？
A: 取决于 PPT 大小和 LLM 响应时间，通常 5-20 秒。

### Q: 如何启用流式输出？
A: 配置 `streaming.enabled: true`，在响应中获得 `streaming_chunks` 数组。

### Q: API 如何处理大文件？
A: 默认支持最大 100MB 的文件，可在 `app.py` 中调整 `max_upload_size`。

## 依赖

- FastAPI - Web 框架
- Uvicorn - ASGI 服务器
- LangChain - LLM 框架
- LangGraph - 工作流编排
- Pydantic - 数据验证
- ChromaDB - 向量数据库
- python-pptx - PPT 处理
- PyMuPDF - PDF 处理

详见 `requirements.txt`。

## 开发

### 添加新的 Agent
1. 在 `agents/base.py` 中创建新类，继承相应的 Agent 接口
2. 实现 `run(state: GraphState) -> GraphState` 方法
3. 在 `PPTExpansionService._build_graph()` 中添加节点
4. 更新 `agents/__init__.py` 导出

### 添加新的知识源
1. 在 `services/mcp_tools.py` 中创建新的 MCP 类
2. 实现 `search(query: str) -> List[Document]` 方法
3. 在 `MCPRouter` 中注册新工具
4. 更新 `services/__init__.py` 导出

## 部署

### Docker 部署
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### 云部署
- 支持 Google Cloud Run
- 支持 AWS Lambda
- 支持 Azure Container Instances

## 测试

运行测试:
```bash
pytest tests/
```

测试覆盖:
- API 端点
- Agent 工作流
- 数据模型验证
- 知识源工具

## 性能优化

1. **缓存**: 启用向量数据库缓存以加快检索
2. **并行处理**: 多 Agent 并行执行
3. **模型选择**: 根据需求选择合适的 LLM 模型
4. **知识源优选**: 根据查询类型选择最佳知识源

## 贡献

欢迎提交 Issue 和 PR！

## 许可

MIT License

## 相关文档

- [快速开始指南](QUICKSTART.md) - 快速上手
- [迁移总结](MIGRATION_SUMMARY.md) - 详细的迁移说明
- [迁移报告](MIGRATION_REPORT.md) - 完整的迁移报告

## 联系方式

如有问题或建议，请提交 Issue。

---

**版本**: 1.0.0  
**最后更新**: 2026-01-20  
**状态**: ✅ 已迁移完成
