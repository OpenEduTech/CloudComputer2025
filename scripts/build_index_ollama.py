import os
import re
import json
import argparse
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import requests
from tqdm import tqdm

import chromadb
from chromadb.config import Settings


# -----------------------------
# Utils (保持原样，未修改)
# -----------------------------
def read_jsonl(path: str) -> List[Dict[str, Any]]:
    items = []
    # 增加路径容错：如果当前目录找不到，尝试去上一级找
    p = Path(path)
    if not p.exists():
        p_alt = Path("..") / path
        if p_alt.exists():
            print(f"[Info] Found jsonl at alternative path: {p_alt}")
            p = p_alt

    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def normalize_text(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def stable_id(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update((str(p) or "").encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def approx_token_len(s: str) -> int:
    return max(1, int(len(s) / 3.2))


def split_paragraphs(text: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not parts:
        parts = [text.strip()]
    return parts


def chunk_sliding(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    text = normalize_text(text)
    paras = split_paragraphs(text)

    chunks = []
    buf = ""
    buf_tokens = 0

    def flush_buffer(b: str):
        b = b.strip()
        if b:
            chunks.append(b)

    for p in paras:
        p_tokens = approx_token_len(p)
        if buf_tokens + p_tokens <= max_tokens:
            buf = (buf + "\n\n" + p).strip()
            buf_tokens = approx_token_len(buf)
        else:
            flush_buffer(buf)

            if overlap_tokens > 0 and chunks:
                tail = chunks[-1]
                tail_keep = int(overlap_tokens * 3.2)
                overlap_text = tail[-tail_keep:].strip()
            else:
                overlap_text = ""

            buf = (overlap_text + "\n\n" + p).strip()
            buf_tokens = approx_token_len(buf)

            while buf_tokens > max_tokens:
                hard_len = int(max_tokens * 3.2)
                head = buf[:hard_len].strip()
                flush_buffer(head)
                buf = buf[hard_len:].strip()
                buf_tokens = approx_token_len(buf)

    flush_buffer(buf)

    uniq = []
    seen = set()
    for c in chunks:
        key = stable_id(c)
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def chunk_table(md: str, max_tokens: int) -> List[str]:
    md = normalize_text(md)
    if approx_token_len(md) <= max_tokens:
        return [md]

    lines = [ln.rstrip() for ln in md.splitlines() if ln.strip()]
    if len(lines) <= 3:
        return chunk_sliding(md, max_tokens=max_tokens, overlap_tokens=0)

    header = lines[:2]
    body = lines[2:]

    chunks = []
    cur = header.copy()
    cur_tokens = approx_token_len("\n".join(cur))

    for ln in body:
        ln_tokens = approx_token_len(ln)
        if cur_tokens + ln_tokens <= max_tokens:
            cur.append(ln)
            cur_tokens = approx_token_len("\n".join(cur))
        else:
            chunks.append("\n".join(cur).strip())
            cur = header.copy() + [ln]
            cur_tokens = approx_token_len("\n".join(cur))

    if len(cur) > len(header):
        chunks.append("\n".join(cur).strip())

    return chunks


# -----------------------------
# Ollama Embeddings (保持原样)
# -----------------------------
def ollama_embed_batch(
        host: str,
        model: str,
        texts: List[str],
        timeout_s: int = 600
) -> List[List[float]]:
    """
    Ollama /api/embeddings 一次只能对一个 prompt 返回 embedding。
    所以这里做 batch 循环（可用 tqdm）。
    """
    url = f"{host}/api/embeddings"
    out = []
    # 简单的重试机制防止网络波动
    for t in texts:
        success = False
        retries = 2
        while retries > 0 and not success:
            try:
                payload = {"model": model, "prompt": t}
                r = requests.post(url, json=payload, timeout=timeout_s)
                r.raise_for_status()
                data = r.json()
                emb = data.get("embedding", None)
                if emb is None:
                    # 如果空则填充0向量防止崩溃
                    out.append([0.0] * 768)
                else:
                    out.append(emb)
                success = True
            except Exception as e:
                retries -= 1
                if retries == 0:
                    print(f"⚠️ Embed failed for chunk: {t[:30]}... Error: {e}")
                    out.append([0.0] * 768)  # Fallback
    return out


# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default="data/parsed_docs.jsonl")
    ap.add_argument("--persist_dir", default="index/chroma")
    ap.add_argument("--collection", default="rag_docs_ollama")

    ap.add_argument("--ollama_host", default=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"))
    ap.add_argument("--embed_model", default=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"))

    ap.add_argument("--batch_size", type=int, default=32)

    ap.add_argument("--max_tokens_text", type=int, default=650)
    ap.add_argument("--overlap_tokens_text", type=int, default=100)
    ap.add_argument("--max_tokens_table", type=int, default=900)
    ap.add_argument("--max_tokens_figure", type=int, default=450)

    args = ap.parse_args()

    # 1. 修复 Host 地址
    if not args.ollama_host.startswith("http"):
        args.ollama_host = f"http://{args.ollama_host}"
    print(f"🔧 [Fix] 强制修复 Ollama 地址为: {args.ollama_host}")

    # 2. 路径处理 (支持 ../index/chroma)
    persist_path = Path(args.persist_dir)
    if not persist_path.is_absolute():
        # 如果当前脚本运行在 scripts/ 下，且 index/ 在 rag/ 下
        if Path("..").joinpath(args.persist_dir).parent.exists():
            persist_path = Path("..") / args.persist_dir

    os.makedirs(persist_path, exist_ok=True)

    # 3. 读取数据
    items = read_jsonl(args.jsonl)
    print(f"[build_index_ollama] loaded records: {len(items)}")
    print(f"[build_index_ollama] ollama_host={args.ollama_host}, embed_model={args.embed_model}")

    # 4. 初始化 Chroma
    client = chromadb.PersistentClient(
        path=str(persist_path),
        settings=Settings(anonymized_telemetry=False)
    )

    try:
        client.delete_collection(args.collection)
    except Exception:
        pass

    col = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine"}
    )

    docs: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    # 5. 数据处理循环
    for rec in items:
        rtype = rec.get("type", "text")
        content = normalize_text(rec.get("content", ""))
        if not content:
            continue

        pdf_name = rec.get("pdf_name") or rec.get("source") or rec.get("file") or "unknown"
        page = rec.get("page", None)
        image_path = rec.get("image_path", None)

        # === 核心修改区：增强 Metadata 构建 ===
        base_meta = {
            "type": rtype,
            "pdf_name": str(pdf_name),
            "page": int(page) if page is not None else -1,
        }

        # 1) 如果有图片路径，必须加上
        if image_path:
            base_meta["image_path"] = str(image_path)

        # 2) [NEW] 自动吸纳 parser 解析出的所有丰富元数据 (Difficulty, Title, FilePath等)
        # 这对于“自动出题”和“精确过滤”至关重要
        if "meta" in rec and isinstance(rec["meta"], dict):
            for k, v in rec["meta"].items():
                # Chroma 的 metadata 只接受 str, int, float, bool
                if isinstance(v, (str, int, float, bool)):
                    base_meta[k] = v
                else:
                    # 遇到 list/dict 等复杂类型，强转为 string 存入，避免报错
                    base_meta[k] = str(v)

        # ------------------------------------

        # 分块逻辑 (保持你原有的精细化处理)
        if rtype == "text":
            chunks = chunk_sliding(content, args.max_tokens_text, args.overlap_tokens_text)
        elif rtype == "table":
            chunks = chunk_table(content, args.max_tokens_table)
        elif rtype == "figure":
            if approx_token_len(content) <= args.max_tokens_figure:
                chunks = [content]
            else:
                chunks = chunk_sliding(content, args.max_tokens_figure, 50)
        else:
            chunks = chunk_sliding(content, args.max_tokens_text, 80)

        for i, ch in enumerate(chunks):
            ch = normalize_text(ch)
            if not ch:
                continue

            # 生成唯一 ID
            cid = stable_id(args.collection, base_meta["pdf_name"], str(base_meta["page"]), rtype, str(i), ch[:80])

            meta = dict(base_meta)
            meta["chunk_idx"] = i
            meta["char_len"] = len(ch)

            docs.append(ch)
            metadatas.append(meta)
            ids.append(cid)

    print(f"[build_index_ollama] prepared chunks: {len(docs)}")

    # 6. ID 去重 (保持原样)
    uniq_docs, uniq_metas, uniq_ids = [], [], []
    seen = set()
    for d, m, i in zip(docs, metadatas, ids):
        if i in seen:
            continue
        seen.add(i)
        uniq_docs.append(d)
        uniq_metas.append(m)
        uniq_ids.append(i)

    docs, metadatas, ids = uniq_docs, uniq_metas, uniq_ids
    print(f"[build_index_ollama] after id-dedup: {len(ids)}")

    if not docs:
        print("Warning: No chunks built. Check your jsonl content fields.")
        return

    # 7. Embedding + 写入 (保持原样)
    for s in tqdm(range(0, len(docs), args.batch_size), desc="embed+add"):
        batch_docs = docs[s:s + args.batch_size]
        batch_ids = ids[s:s + args.batch_size]
        batch_metas = metadatas[s:s + args.batch_size]

        emb = ollama_embed_batch(args.ollama_host, args.embed_model, batch_docs)

        # 确保格式正确
        emb = np.asarray(emb, dtype=np.float32).tolist()

        col.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas,
            embeddings=emb
        )

    # 8. 保存清单
    manifest = {
        "jsonl": args.jsonl,
        "persist_dir": str(persist_path),
        "collection": args.collection,
        "ollama_host": args.ollama_host,
        "embedding_model": args.embed_model,
        "total_records": len(items),
        "total_chunks_added": len(ids),
    }

    # 路径容错
    index_manifest_dir = Path("index")
    if not index_manifest_dir.parent.exists():
        if Path("..").joinpath("index").exists():
            index_manifest_dir = Path("..") / "index"
    index_manifest_dir.mkdir(parents=True, exist_ok=True)

    with open(index_manifest_dir / "index_manifest_ollama.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("[build_index_ollama] DONE. manifest saved.")


if __name__ == "__main__":
    main()
