import json
import os
import shutil
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
EMBED_MODEL = os.getenv("EMBED_MODEL", "embedding-3")
EMBED_DIM = int(os.getenv("EMBED_DIM", "0"))
EMBED_MAX_CHARS = int(os.getenv("EMBED_MAX_CHARS", "2000"))
RAG_ENABLED = os.getenv("RAG_ENABLED", "1") == "1"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
RAG_CONTEXT_MAX_CHARS = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "8000"))
RAG_RETRY_MAX = int(os.getenv("RAG_RETRY_MAX", "3"))
RAG_RETRY_BASE_SEC = float(os.getenv("RAG_RETRY_BASE_SEC", "1.0"))
RAG_RETRY_MAX_SEC = float(os.getenv("RAG_RETRY_MAX_SEC", "6.0"))
RAG_INDEX_DIR = Path(os.getenv("RAG_INDEX_DIR", "storage/vector_index"))
ZHIPU_EMBED_URL = os.getenv(
    "ZHIPU_EMBED_URL", "https://open.bigmodel.cn/api/paas/v4/embeddings"
)


def _sleep_with_backoff(attempt: int) -> None:
    delay = min(RAG_RETRY_BASE_SEC * (2 ** (attempt - 1)), RAG_RETRY_MAX_SEC)
    time.sleep(delay)


def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _extract_embedding(resp: Dict[str, Any]) -> List[float]:
    if not isinstance(resp, dict):
        return []
    if isinstance(resp.get("data"), list) and resp["data"]:
        item = resp["data"][0]
        if isinstance(item, dict):
            emb = item.get("embedding") or item.get("vector")
            if isinstance(emb, list):
                return emb
    if isinstance(resp.get("embedding"), list):
        return resp["embedding"]
    if isinstance(resp.get("output"), list) and resp["output"]:
        item = resp["output"][0]
        if isinstance(item, dict):
            emb = item.get("embedding") or item.get("vector")
            if isinstance(emb, list):
                return emb
    return []


def embed_text(text: str) -> List[float]:
    if not RAG_ENABLED:
        return []
    if not ZHIPU_API_KEY:
        raise RuntimeError("ZHIPU_API_KEY is required for embeddings")
    content = str(text or "").strip()
    if not content:
        return []
    content = content[:EMBED_MAX_CHARS]
    payload: Dict[str, Any] = {"model": EMBED_MODEL, "input": content}
    if EMBED_DIM > 0:
        payload["dimensions"] = EMBED_DIM

    last_exc: Exception | None = None
    for attempt in range(1, RAG_RETRY_MAX + 1):
        try:
            resp = _post_json(ZHIPU_EMBED_URL, payload)
            vec = _extract_embedding(resp)
            if not vec:
                raise RuntimeError("empty embedding response")
            return [float(x) for x in vec]
        except Exception as exc:
            last_exc = exc
            if attempt < RAG_RETRY_MAX:
                _sleep_with_backoff(attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    return []


class ZhipuEmbeddings(Embeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [embed_text(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return embed_text(text)


def _index_path(material_id: str) -> Path:
    safe_id = str(material_id).strip()
    return RAG_INDEX_DIR / safe_id


def build_embeddings(
    db,
    material_id: str,
    chunks: List[str],
    student_id: Optional[str],
    notebook_id: Optional[str],
) -> int:
    if not RAG_ENABLED:
        return 0
    if not chunks:
        return 0
    now = datetime.utcnow()
    documents: List[Document] = []
    for idx, chunk in enumerate(chunks):
        content = str(chunk or "").strip()
        if not content:
            continue
        metadata = {
            "material_id": material_id,
            "chunk_index": idx,
            "created_at": now.isoformat(),
        }
        if student_id:
            metadata["student_id"] = student_id
        if notebook_id:
            metadata["notebook_id"] = notebook_id
        documents.append(Document(page_content=content, metadata=metadata))

    if not documents:
        return 0

    index_dir = _index_path(material_id)
    if index_dir.exists():
        shutil.rmtree(index_dir, ignore_errors=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    store = FAISS.from_documents(documents, ZhipuEmbeddings())
    store.save_local(str(index_dir))
    return len(documents)


def _load_store(material_id: str) -> Optional[FAISS]:
    index_dir = _index_path(material_id)
    if not index_dir.exists():
        return None
    return FAISS.load_local(
        str(index_dir),
        ZhipuEmbeddings(),
        allow_dangerous_deserialization=True,
    )


def _similarity_search(
    store: FAISS,
    query: str,
    query_vec: List[float],
    top_k: int,
) -> List[Tuple[Document, float]]:
    if hasattr(store, "similarity_search_with_score_by_vector") and query_vec:
        return store.similarity_search_with_score_by_vector(query_vec, k=top_k)
    return store.similarity_search_with_score(query, k=top_k)


def retrieve_context(
    db,
    material_ids: List[str],
    query: str,
    student_id: Optional[str],
    notebook_id: Optional[str],
    max_chars: Optional[int] = None,
    top_k: Optional[int] = None,
) -> str:
    if not RAG_ENABLED:
        return ""
    if not material_ids:
        return ""
    if not query or not query.strip():
        return ""
    qvec = embed_text(query)
    if not qvec:
        return ""
    k = top_k or RAG_TOP_K
    limit_chars = max_chars or RAG_CONTEXT_MAX_CHARS

    candidates: List[Tuple[float, str]] = []
    for mid in material_ids:
        store = _load_store(mid)
        if not store:
            continue
        try:
            docs_with_score = _similarity_search(store, query, qvec, k)
        except Exception:
            continue
        for doc, score in docs_with_score:
            if not doc or not doc.page_content:
                continue
            candidates.append((float(score), doc.page_content))

    if not candidates:
        return ""
    # FAISS returns L2 distance: lower is better
    candidates.sort(key=lambda x: x[0])
    collected: List[str] = []
    total = 0
    for _, chunk in candidates:
        if total + len(chunk) > limit_chars:
            break
        collected.append(chunk)
        total += len(chunk)
        if total >= limit_chars:
            break
    return "\n".join(collected)
