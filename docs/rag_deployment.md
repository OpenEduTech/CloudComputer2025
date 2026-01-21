# RAG 部署与调试指南

## 1. 环境准备

确保你已安装 Docker Desktop，并且网络可以拉取 Docker 镜像。

### 配置文件
项目根目录下的 `.env` 文件应包含以下内容：
```bash
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
OPENAI_API_KEY=your_api_key_here
```

## 2. 启动服务

在项目根目录下运行：
```bash
docker-compose up -d --build
```
这将启动包括 `chromadb` 和 `worker` 在内的所有服务。

## 3. 数据导入

服务启动后，需要将预处理好的心理学数据导入 ChromaDB。我们提供了一个脚本来自动完成此操作。

### 方法 A: 在 Worker 容器内执行 (推荐)
```bash
# 进入 worker 容器
docker-compose exec worker bash

# 运行导入脚本
python tools/ingest_data.py
```
成功后，你应该看到 "Ingestion complete" 的提示。

### 数据格式说明
数据文件位于 `data/psychology_data.json`，格式如下：
```json
[
  {
    "keyword": "熵",
    "content": "详细解释...",
    "source": "来源引用"
  }
]
```

### 方法 B: 导入电子书 (.epub / .mobi)
我们已支持直接扫描 `data/` 目录下的电子书文件。

```bash
# 在 worker 容器内
python tools/ingest_books.py
```
该脚本会自动递归扫描 `data/` 目录，解析所有 `.epub` 和 `.mobi` 文件，进行分块并存入向量数据库。

## 4. 测试 RAG 搜索

导入数据后，可以使用 `rag_retriever.py` 进行测试。

```bash
# 在 worker 容器内
python tools/rag_retriever.py
```
该脚本会搜索 "熵" 并打印相关结果。

## 5. API 与参数说明

### 嵌入模型
我们使用 `paraphrase-multilingual-MiniLM-L12-v2` 模型，它支持多种语言（包括中文），生成的向量维度为 384 (注意：MiniLM-L12-v2 是 384 维，如果需要 768 维可以使用 `paraphrase-multilingual-mpnet-base-v2`，请在 docker-compose.yml 中修改 `EMBEDDING_MODEL` 环境变量)。

*当前配置*: `paraphrase-multilingual-MiniLM-L12-v2` (速度快，效果好)

### ChromaDB 集合
- **Collection Name**: `psychology_knowledge`
- **Metadata**: 包含 `keyword` 和 `source`

### 离线模型提示
如果在容器内下载模型失败（网络原因），可以手动下载 `paraphrase-multilingual-mpnet-base-v2` 模型文件，挂载到容器中，并修改代码加载本地路径。

## 6. 故障排查

- **Docker 拉取失败**: 请检查网络连接或配置 Docker 镜像加速器。
- **ChromaDB 连接失败**: 确保 `docker-compose.yml` 中 `worker` 服务正确依赖 `chromadb`，且环境变量 `CHROMA_SERVER_HOST=chromadb` 设置正确。
- **搜索无结果**: 检查数据是否成功导入（使用 `ingest_data.py`），或尝试降低搜索阈值。
