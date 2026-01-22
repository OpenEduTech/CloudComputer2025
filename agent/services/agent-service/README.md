# Knowledge Graph Agent Service

跨学科知识图谱生成服务：输入 concept，输出 GraphJSON（meta / nodes / edges）。

## 1. 功能概览

- 输入：概念词 `concept`（中文为主）
- 输出：符合 `schema/graph.schema.json` 的 GraphJSON
- Pipeline：Step0 → Step1 → Step2 → Step3 → Step4
- 服务接口：FastAPI

## 2. 目录结构

services/agent-service/
├── api.py
├── agent_pipeline.py
├── llm_client.py
├── step4_postprocess.py
├── prompts/
│ ├── step0_normalize.txt
│ ├── step1_candidates.txt
│ ├── step2_enrich.txt
│ └── step3_edges.txt
├── schema/
│ └── graph.schema.json
├── requirements.txt
├── .env.example
└── README.md


## 3. 环境变量

复制环境变量模板：

```bash
cp .env.example .env
编辑 .env，至少填写：

DEEPSEEK_API_KEY

其余可默认。


## 4. 本地运行（推荐 venv）

创建虚拟环境：

python -m venv .venv
source .venv/bin/activate


安装依赖：

pip install -r requirements.txt


启动服务：

uvicorn api:app --host 0.0.0.0 --port 8000 --reload

## 5. 测试接口

5.1 健康检查
curl http://localhost:8000/healthz

返回：

{"ok": true}

5.2 生成图谱（debug=true 会返回中间结果）
curl -X POST http://localhost:8000/generate_graph \
  -H "Content-Type: application/json" \
  -d '{"concept":"熵","debug":true}'
