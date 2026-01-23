import os
import logging
import requests
import chromadb
import torch
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from chromadb.config import Settings
# from FlagEmbedding import FlagReranker
from neo4j import GraphDatabase

# ================= 1. 关键路径配置 =================
CURRENT_SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent

CHROMA_DIR = Path(os.getenv("CHROMA_DIR", PROJECT_ROOT / "index" / "chroma"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "rag_docs_ollama")
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
DOCS_DIR = Path(os.getenv("DOCS_DIR", PROJECT_ROOT / "docs"))
MANUAL_DIR = DOCS_DIR / "manual"

# 🌟 设置端口为 8088 (匹配前端)，Host 设置为 127.0.0.1
CURRENT_PORT = 8088
HOST_URL = f"http://127.0.0.1:{CURRENT_PORT}"

# ================= 2. 模型配置 =================
_raw_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11435")
if not _raw_host.startswith("http"): _raw_host = f"http://{_raw_host}"
OLLAMA_HOST = _raw_host

OLLAMA_LLM_MODEL = "qwen2.5:7b-instruct"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
USE_RERANKER = False

# ⚠️⚠️⚠️ 这里必须填对您的 Neo4j 密码！⚠️⚠️⚠️
# 如果之前的报错是 Unauthorized，说明 "password123" 是错的
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

TOPK_RECALL = 15
TOPK_CONTEXT = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Service Optimized")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

if DATA_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DATA_DIR)), name="assets")
if DOCS_DIR.exists():
    app.mount("/doc_assets", StaticFiles(directory=str(DOCS_DIR)), name="doc_assets")


class AskRequest(BaseModel):
    question: str
    where: Optional[Dict[str, Any]] = None


class AskResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]


class GraphData(BaseModel):
    nodes: List[Dict]
    links: List[Dict]


# ================= 工具函数 =================

def convert_path_to_url(local_path: str) -> str:
    if not local_path: return ""
    p = str(local_path).replace("\\", "/")
    if p.startswith("http"): return p
    if p.startswith("docs/"):
        return f"{HOST_URL}/doc_assets/{p[5:]}"
    elif "data/" in p:
        rel = p.split("data/")[-1]
        return f"{HOST_URL}/assets/{rel}"
    return f"{HOST_URL}/doc_assets/{p}"


def fix_markdown_images(text: str) -> str:
    if not text: return ""
    text = text.replace("](../pic/", f"]({HOST_URL}/doc_assets/pic/")
    text = text.replace("](.../pic/", f"]({HOST_URL}/doc_assets/pic/")
    text = text.replace("](docs/pic/", f"]({HOST_URL}/doc_assets/pic/")
    text = text.replace("](./pic/", f"]({HOST_URL}/doc_assets/pic/")
    return text


def ollama_embed(text: str):
    try:
        r = requests.post(f"{OLLAMA_HOST}/api/embeddings",
                          json={"model": OLLAMA_EMBED_MODEL, "prompt": text}, timeout=10)
        return r.json().get("embedding")
    except:
        return []


def ollama_generate(prompt: str):
    try:
        payload = {
            "model": OLLAMA_LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_ctx": 4096}
        }
        r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
        return r.json().get("response", "").strip()
    except Exception as e:
        return f"LLM Error: {e}"


def build_prompt(question: str, contexts: List[str]) -> str:
    fixed_contexts = [fix_markdown_images(c) for c in contexts]
    context_str = "\n\n".join([f"【已知信息 {i + 1}】\n{c}" for i, c in enumerate(fixed_contexts)])
    return f"""
你是一个编程辅导助手。请基于已知信息回答。

【已知信息】：
{context_str}

**要求**：
1. 若用户要求出题，请设计题目。
2. 保留图片链接。

**问题**：
{question}
""".strip()


def doc_to_context(doc: str, md: Dict[str, Any]) -> str:
    src = md.get("pdf_name", "") or md.get("source", "")
    header = f"[来源: {src}]"
    if md.get("image_path"):
        header += f"\n[参考图片]: ![]({convert_path_to_url(md['image_path'])})"
    return header + "\n" + doc


# ================= 全局实例 =================
chroma_client = None
collection = None
neo4j_driver = None


@app.on_event("startup")
def startup():
    global chroma_client, collection, neo4j_driver
    print("\n" + "=" * 50)
    print("🚀 系统启动自检中...")

    if MANUAL_DIR.exists():
        print(f"✅ 发现 Manual 目录: {MANUAL_DIR}")
    else:
        print(f"❌ 警告: Manual 目录不存在: {MANUAL_DIR}")

    try:
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
        collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
        print("✅ ChromaDB 连接成功")
    except:
        print("❌ ChromaDB 连接失败")

    # Neo4j 连接逻辑
    try:
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        # 尝试验证连接，如果密码错误这里会报错
        neo4j_driver.verify_connectivity()
        print("✅ Neo4j 连接成功")
    except Exception as e:
        print(f"⚠️ Neo4j 连接失败 (不影响聊天功能): {e}")
        print("👉 请检查代码中 NEO4J_PASSWORD 是否正确！")

    print("=" * 50 + "\n")


@app.on_event("shutdown")
def shutdown():
    if neo4j_driver: neo4j_driver.close()


# ================= 3. API 接口 =================

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    q = req.question.strip()
    q_lower = q.lower()
    if not q: return {"answer": "Empty question", "citations": []}

    quiz_keywords = ["出题", "考考", "generate", "quiz", "test me", "exercise"]
    is_quiz = any(k in q_lower for k in quiz_keywords)
    lcs_keywords = ["lcs", "最长公共子序列"]
    is_lcs = any(k in q_lower for k in lcs_keywords)

    print(f"\n🔍 [Ask] '{q}' -> is_lcs={is_lcs}, is_quiz={is_quiz}")

    # 场景 A: 直通车
    if is_lcs and not is_quiz:
        manual_file = MANUAL_DIR / "LCS_Solution.md"
        if not manual_file.exists():
            return {"answer": f"⚠️ 文件未找到: {manual_file}", "citations": []}

        print("🚀 [Route] 直通 Manual 文件")
        raw_content = manual_file.read_text(encoding="utf-8")
        return {
            "answer": fix_markdown_images(raw_content),
            "citations": [{"evidence_id": 1, "score": 1.0, "source": "LCS_Solution.md", "type": "manual"}]
        }

    # 场景 B: RAG
    print("🤖 [Route] 标准 RAG (Ollama)")
    q_emb = ollama_embed(q)
    if not q_emb: return {"answer": "Embedding failed", "citations": []}

    res = collection.query(query_embeddings=[q_emb], n_results=TOPK_RECALL, where=req.where)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]

    if not docs: return {"answer": "未找到相关内容。", "citations": []}

    candidates = [{"doc": d, "meta": m or {}} for d, m in zip(docs, metas)]
    top = candidates[:TOPK_CONTEXT]
    contexts = [doc_to_context(t["doc"], t["meta"]) for t in top]
    prompt = build_prompt(q, contexts)
    ans = ollama_generate(prompt)

    citations = []
    for i, item in enumerate(top):
        citations.append({
            "evidence_id": i + 1,
            "score": 0.9,
            "source": item["meta"].get("pdf_name", "unknown"),
            "image_url": convert_path_to_url(item["meta"].get("image_path", "")),
            "type": "text"
        })

    return {"answer": ans, "citations": citations}


# 🌟🌟🌟 补全 Graph 接口 (必须有这个前端才能显示图谱) 🌟🌟🌟
@app.get("/graph/overview", response_model=GraphData)
def graph_overview(limit: int = 100):
    # 如果驱动没连上，直接返回空
    if not neo4j_driver:
        print("❌ [Graph] Neo4j driver is None (Authentication failed?)")
        return {"nodes": [], "links": []}

    try:
        print(f"🔍 [Graph] Querying Neo4j (Limit {limit})...")
        with neo4j_driver.session() as session:
            # 兼容不同版本的 Neo4j 驱动返回
            res = session.run(f"MATCH (n)-[r]->(m) RETURN n,r,m LIMIT {limit}")
            nodes = {}
            links = []

            for rec in res:
                n, m, r = rec['n'], rec['m'], rec['r']

                # 安全获取 ID
                n_id = str(n.element_id) if hasattr(n, 'element_id') else str(n.id)
                m_id = str(m.element_id) if hasattr(m, 'element_id') else str(m.id)

                # 安全获取 Label
                n_lbl = list(n.labels)[0] if n.labels else "Entity"
                m_lbl = list(m.labels)[0] if m.labels else "Entity"

                nodes[n_id] = {"id": n_id, "label": n_lbl, "name": n.get("name", n_lbl)}
                nodes[m_id] = {"id": m_id, "label": m_lbl, "name": m.get("name", m_lbl)}
                links.append({"source": n_id, "target": m_id, "type": r.type})

            print(f"✅ [Graph] Success! Found {len(nodes)} nodes, {len(links)} links.")
            return {"nodes": list(nodes.values()), "links": links}

    except Exception as e:
        print(f"❌ [Graph Error]: {e}")
        traceback.print_exc()
        return {"nodes": [], "links": []}


if __name__ == "__main__":
    import uvicorn

    # 绑定 0.0.0.0 和 端口 8088
    print(f"🚀 服务启动中: http://127.0.0.1:{CURRENT_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=CURRENT_PORT)
