# 跨学科知识图谱智能体（增强版）

本项目为《智能体云原生开发》期末大作业命题三：**跨学科知识图谱智能体**的实现。

## 核心能力（增强点）
- **多学科强制覆盖**：至少 5 个学科（必含 数学 / 计算机科学 / 生物学）
- **多跳扩展**：一跳概念 + 关键概念二跳扩展（更丰富的知识网）
- **桥梁关系**：显式构建跨学科“桥梁边”（概念之间的推理链路）
- **证据修正（可选）**：若配置 Tavily API Key，会对部分关系进行 Web 证据收集并进行保守修正
- **云原生部署**：Docker + docker-compose 一键启动（后端 + Neo4j）

---

## 一键启动（推荐：Docker Compose）

1) 准备 `.env`（不要提交真实 key；建议同时提供 `.env.example`）
```env
OPENAI_API_KEY=xxx
TAVILY_API_KEY=xxx
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.2
NEO4J_PASSWORD=YourStrongPassword123
```

2) 启动
```bash
docker compose up --build
```

3) 访问
- 前端： http://localhost:8000/
- Neo4j Browser： http://localhost:17474/ （用户名 neo4j，密码为 NEO4J_PASSWORD）

---

## 本地运行（不建议：需要本地 Neo4j）
```bash
pip install -r requirements.txt
python main.py
```

---

## 接口
- `GET /api/graph?concept=xxx&write_neo4j=true`
  - 返回 nodes/edges JSON（包含 confidence 与推理 logic）
  - `write_neo4j=false` 可仅返回 JSON，不写入数据库
