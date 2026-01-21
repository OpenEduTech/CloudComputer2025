import re
from collections import Counter


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_WORD_RE = re.compile(r"[a-zA-Z0-9]+")


def _normalize(text: str) -> str:
    return text.replace("\n", " ").strip()


def _has_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def _extract_units(text: str) -> list[str]:
    """
    简易切分：中文用双字切片，英文用词粒度。
    """
    text = _normalize(text)
    if not text:
        return []
    if _has_cjk(text):
        clean = re.sub(r"\s+", "", text)
        return [clean[i : i + 2] for i in range(len(clean) - 1)]
    return _WORD_RE.findall(text.lower())


def _build_counter(text: str) -> Counter:
    return Counter(_extract_units(text))


def select_chunks_for_generation(chunks: list[dict], top_k: int = 10) -> list[dict]:
    """
    为出题挑选代表性片段：根据高频关键词打分，取前 top_k。
    """
    if not chunks:
        return []
    counters = [(_build_counter(c.get("text", "")), c) for c in chunks]
    global_counter = Counter()
    for counter, _ in counters:
        global_counter.update(counter)
    keywords = {k for k, _ in global_counter.most_common(60)}
    scored = []
    for idx, (counter, chunk) in enumerate(counters):
        score = sum(counter.get(k, 0) for k in keywords)
        scored.append((score, idx, chunk))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, _, c in scored[:top_k]]


def select_chunks_for_question(chunks: list[dict], question: str, answer: str | None = None, top_k: int = 3) -> list[dict]:
    """
    为判卷挑选相关片段：问题与参考答案作为查询。
    """
    if not chunks:
        return []
    query = f"{question} {answer or ''}".strip()
    query_counter = _build_counter(query)
    if not query_counter:
        return chunks[:top_k]
    scored = []
    for idx, chunk in enumerate(chunks):
        counter = _build_counter(chunk.get("text", ""))
        score = sum(counter.get(k, 0) for k in query_counter.keys())
        scored.append((score, idx, chunk))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, _, c in scored[:top_k]]
