import os
import re
import json
import argparse
import hashlib
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
from tqdm import tqdm

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


# -----------------------------
# Utils
# -----------------------------
def read_jsonl(path: str) -> List[Dict[str, Any]]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
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
        h.update((p or "").encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def approx_token_len(s: str) -> int:
    # 粗略 token 估算（足够用于 chunk）
    # 中文/英文混合时：按字符与空格都估一下
    return max(1, int(len(s) / 3.2))


def split_paragraphs(text: str) -> List[str]:
    # 尽量按段落切
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not parts:
        parts = [text.strip()]
    return parts


def chunk_sliding(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    """
    先按段落聚合，再做滑窗，避免切断太碎。
    """
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
            # 先把当前 buffer 输出
            flush_buffer(buf)

            # 处理重叠：从上一 chunk 尾部截一段
            if overlap_tokens > 0 and chunks:
                tail = chunks[-1]
                tail_words = list(tail)
                # 粗略：用字符截取实现 overlap（对中文更稳）
                tail_keep = int(overlap_tokens * 3.2)
                overlap_text = "".join(tail_words[-tail_keep:]).strip()
            else:
                overlap_text = ""

            buf = (overlap_text + "\n\n" + p).strip()
            buf_tokens = approx_token_len(buf)

            # 如果单段太长，硬切
            while buf_tokens > max_tokens:
                hard_len = int(max_tokens * 3.2)
                head = buf[:hard_len].strip()
                flush_buffer(head)
                buf = buf[hard_len:].strip()
                buf_tokens = approx_token_len(buf)

    flush_buffer(buf)
    # 最后去重（同一文档重复 chunk 常见）
    uniq = []
    seen = set()
    for c in chunks:
        key = stable_id(c)
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def chunk_table(md: str, max_tokens: int) -> List[str]:
    """
    表格优先整表；过大则按行块切（保留表头）
    """
    md = normalize_text(md)
    if approx_token_len(md) <= max_tokens:
        return [md]

    lines = [ln.rstrip() for ln in md.splitlines() if ln.strip()]
    if len(lines) <= 3:
        # 太短也没法切
        return chunk_sliding(md, max_tokens=max_tokens, overlap_tokens=0)

    header = lines[:2]  # 假设 markdown table: header + --- 分隔
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
# Main build
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default="data/parsed_docs.jsonl")
    ap.add_argument("--persist_dir", default="index/chroma")
    ap.add_argument("--collection", default="rag_docs")
    ap.add_argument("--model", default="BAAI/bge-m3", help="SentenceTransformer model name")
    ap.add_argument("--device", default=None, help="cpu/cuda, leave empty for auto")
    ap.add_argument("--batch_size", type=int, default=32)

    # chunk params
    ap.add_argument("--max_tokens_text", type=int, default=650)
    ap.add_argument("--overlap_tokens_text", type=int, default=100)
    ap.add_argument("--max_tokens_table", type=int, default=900)
    ap.add_argument("--max_tokens_figure", type=int, default=450)

    args = ap.parse_args()

    os.makedirs(args.persist_dir, exist_ok=True)

    # 1) Load parsed docs
    items = read_jsonl(args.jsonl)
    print(f"[build_index] loaded records: {len(items)} from {args.jsonl}")

    # 2) Prepare embedding model
    device = args.device
    model = SentenceTransformer(args.model, device=device)  # auto if device None
    emb_dim = model.get_sentence_embedding_dimension()
    print(f"[build_index] embedding model: {args.model} (dim={emb_dim})")

    # 3) Chroma client
    client = chromadb.PersistentClient(
        path=args.persist_dir,
        settings=Settings(anonymized_telemetry=False)
    )

    # create or get collection
    col = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine"}
    )

    # 4) Build chunks
    docs: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    for rec in items:
        rtype = rec.get("type", "text")
        content = normalize_text(rec.get("content", ""))
        if not content:
            continue

        pdf_name = rec.get("pdf_name") or rec.get("source") or rec.get("file") or "unknown"
        page = rec.get("page", None)
        image_path = rec.get("image_path", None)

        # You may have your own fields like: table_flavor, bbox, etc.
        base_meta = {
            "type": rtype,
            "pdf_name": str(pdf_name),
            "page": int(page) if page is not None else -1,
        }
        if image_path:
            base_meta["image_path"] = str(image_path)

        # chunk by type
        if rtype == "text":
            chunks = chunk_sliding(
                content,
                max_tokens=args.max_tokens_text,
                overlap_tokens=args.overlap_tokens_text
            )
        elif rtype == "table":
            chunks = chunk_table(content, max_tokens=args.max_tokens_table)
            if "table_flavor" in rec:
                base_meta["table_flavor"] = str(rec["table_flavor"])
        elif rtype == "figure":
            # figure caption one per chunk unless very long
            if approx_token_len(content) <= args.max_tokens_figure:
                chunks = [content]
            else:
                chunks = chunk_sliding(content, max_tokens=args.max_tokens_figure, overlap_tokens=50)
        else:
            # fallback
            chunks = chunk_sliding(content, max_tokens=args.max_tokens_text, overlap_tokens=80)

        for i, ch in enumerate(chunks):
            ch = normalize_text(ch)
            if not ch:
                continue

            cid = stable_id(args.collection, base_meta["pdf_name"], str(base_meta["page"]), rtype, str(i), ch[:80])
            meta = dict(base_meta)
            meta["chunk_idx"] = i
            meta["char_len"] = len(ch)

            docs.append(ch)
            metadatas.append(meta)
            ids.append(cid)

    print(f"[build_index] prepared chunks: {len(docs)}")

    # ---- Ensure unique IDs (dedup by id) ----
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
        raise RuntimeError("No chunks built. Check your jsonl content fields.")

    # 5) Dedup against existing ids in collection (avoid duplicate insert on re-run)
    # Chroma doesn't provide bulk-exists, so we do a simple try-add strategy:
    # We'll add in batches; duplicates will raise sometimes depending on chroma version.
    # Safer: query by ids in small batches and filter.


    # 6) Embed + add
    for s in tqdm(range(0, len(docs), args.batch_size), desc="embed+add"):
        batch_docs = docs[s:s + args.batch_size]
        batch_ids = ids[s:s + args.batch_size]
        batch_metas = metadatas[s:s + args.batch_size]

        emb = model.encode(batch_docs, normalize_embeddings=True, batch_size=args.batch_size, show_progress_bar=False)
        emb = np.asarray(emb, dtype=np.float32).tolist()

        col.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas,
            embeddings=emb
        )

    # 7) Save manifest
    manifest = {
        "jsonl": args.jsonl,
        "persist_dir": args.persist_dir,
        "collection": args.collection,
        "embedding_model": args.model,
        "chunk_params": {
            "max_tokens_text": args.max_tokens_text,
            "overlap_tokens_text": args.overlap_tokens_text,
            "max_tokens_table": args.max_tokens_table,
            "max_tokens_figure": args.max_tokens_figure,
        },
        "total_records": len(items),
        "total_chunks_built": len(docs),
        "total_chunks_added": len(new_ids),
    }
    os.makedirs("index", exist_ok=True)
    with open("index/index_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("[build_index] DONE. manifest saved to index/index_manifest.json")
    print(f"[build_index] Chroma persist dir: {args.persist_dir}, collection: {args.collection}")


if __name__ == "__main__":
    main()
