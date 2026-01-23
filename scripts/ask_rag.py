import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import torch

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from FlagEmbedding import FlagReranker

from transformers import AutoTokenizer, AutoModelForCausalLM


# -----------------------------
# Config
# -----------------------------
PERSIST_DIR = Path("index/chroma")          # 你的 Chroma 持久化目录
COLLECTION_NAME = "rag_docs"               # build_index.py 里用的 collection 名称（确保一致）
EMB_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"

# 你可以按机器情况改：
LLM_NAME = "Qwen/Qwen2.5-7B-Instruct"


# -----------------------------
# Load retriever (Chroma)
# -----------------------------
def load_retriever():
    if not PERSIST_DIR.exists():
        raise RuntimeError(f"Chroma persist_dir not found: {PERSIST_DIR}. Run build_index first.")

    emb = HuggingFaceEmbeddings(
        model_name=EMB_MODEL,
        model_kwargs={"device": "cpu"},  # embedding 用 cpu 更稳；你也可以改 cuda
        encode_kwargs={"normalize_embeddings": True},
    )

    db = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=emb,
        persist_directory=str(PERSIST_DIR),
    )
    return db


# -----------------------------
# Prompt (anti-hallucination + citation)
# -----------------------------
def build_prompt(question: str, contexts: List[str]) -> str:
    ctx = "\n\n".join([f"[证据{i+1}]\n{c}" for i, c in enumerate(contexts)])
    return f"""你是一个严谨的知识库问答助手。只能根据给定证据回答，禁止凭空编造。
如果证据不足以回答，请明确说“证据不足”，并说明缺少什么信息。
回答必须引用证据编号，例如：引用：[1][3]。

问题：{question}

证据：
{ctx}

请用中文作答：
"""


# -----------------------------
# Optional: format doc with metadata for better grounding
# -----------------------------
def doc_to_context(d) -> str:
    # LangChain Document: d.page_content, d.metadata
    md = d.metadata or {}
    src = md.get("pdf_name") or md.get("source") or md.get("file") or ""
    page = md.get("page", "")
    dtype = md.get("type", "")
    chunk = md.get("chunk_idx", "")
    img = md.get("image_path", "")

    header = f"(source={src}, page={page}, type={dtype}, chunk={chunk})"
    if img:
        header += f"\n(image_path={img})"
    return header + "\n" + d.page_content


# -----------------------------
# Main
# -----------------------------
def main():
    question = input("请输入问题：").strip()
    if not question:
        print("Empty question.")
        return

    db = load_retriever()

    # 你可以在这里加 metadata 过滤（高分：类型/特定 pdf/页码）
    # 示例：
    # where = {"type": "table"}
    # docs = db.similarity_search(question, k=12, filter=where)
    where = None
    docs = db.similarity_search(question, k=12, filter=where)

    if not docs:
        print("没有召回到任何证据。")
        return

    # 组候选：用 doc_to_context 把 metadata 放进上下文（非常有用）
    candidates = [doc_to_context(d) for d in docs]

    # 2) reranker 重排
    # 注意：use_fp16 只有在你有 CUDA/合适显卡时才建议 True，否则改 False
    use_fp16 = torch.cuda.is_available()
    reranker = FlagReranker(RERANK_MODEL, use_fp16=use_fp16)
    pairs = [[question, c] for c in candidates]
    scores = reranker.compute_score(pairs)

    ranked = sorted(zip(scores, candidates, docs), key=lambda x: x[0], reverse=True)
    top = ranked[:4]
    contexts = [t[1] for t in top]

    # 3) LLM 生成
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(LLM_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        LLM_NAME,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
    )
    if device == "cpu":
        model.to("cpu")

    prompt = build_prompt(question, contexts)

    inputs = tokenizer(prompt, return_tensors="pt")
    if device == "cuda":
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.2,
            top_p=0.9,
        )

    answer = tokenizer.decode(out[0], skip_special_tokens=True)
    print("\n===== 回答 =====\n")
    print(answer[len(prompt):].strip())

    # 4) 打印证据溯源
    print("\n===== 证据来源（Top4） =====")
    for i, (score, ctx, d) in enumerate(top, 1):
        md = d.metadata or {}
        src = md.get("pdf_name") or md.get("source") or ""
        page = md.get("page", "")
        dtype = md.get("type", "")
        chunk = md.get("chunk_idx", "")
        print(f"[{i}] score={score:.4f} source={src} page={page} type={dtype} chunk={chunk}")

if __name__ == "__main__":
    main()
