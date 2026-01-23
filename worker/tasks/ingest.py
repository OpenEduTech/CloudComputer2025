import json
import os
import re
import time
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from groq import Groq
from openai import OpenAI
from pymongo import MongoClient

from tasks.rag import build_embeddings, RAG_ENABLED

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "learning_agent")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")
SUMMARY_MAX_CHARS = int(os.getenv("SUMMARY_MAX_CHARS", "10000"))
SUMMARY_CHUNK_CHARS = int(os.getenv("SUMMARY_CHUNK_CHARS", "4000"))


# --- Zhipu (GLM) for prompt compression (avoid token limit in knowledge-tree generation) ---
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_CHAT_URL = os.getenv("ZHIPU_CHAT_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
ZHIPU_SUMMARY_MODEL = os.getenv("ZHIPU_SUMMARY_MODEL", os.getenv("ZHIPU_MODEL", "glm-4-flash"))
TREE_COMPRESS_ENABLED = os.getenv("TREE_COMPRESS_ENABLED", "1") == "1"
TREE_COMPRESS_MAX_CHARS = int(os.getenv("TREE_COMPRESS_MAX_CHARS", "6000"))
TREE_COMPRESS_CHUNK_CHARS = int(os.getenv("TREE_COMPRESS_CHUNK_CHARS", "3500"))
TREE_COMPRESS_RETRY_MAX = int(os.getenv("TREE_COMPRESS_RETRY_MAX", "3"))

# M2：知识树生成输入长度（避免超长）
TREE_CONTEXT_MAX_CHARS = int(os.getenv("TREE_CONTEXT_MAX_CHARS", "12000"))
TREE_CANDIDATE_MAX = int(os.getenv("TREE_CANDIDATE_MAX", "30"))
TREE_EXTRACT_MODE = os.getenv("TREE_EXTRACT_MODE", "single").lower()
TREE_STAGE_CHAPTER_MAX = int(os.getenv("TREE_STAGE_CHAPTER_MAX", "15"))
TREE_STAGE_SECTION_MAX = int(os.getenv("TREE_STAGE_SECTION_MAX", "10"))
TREE_STAGE_POINT_MAX = int(os.getenv("TREE_STAGE_POINT_MAX", "10"))
TREE_RAG_TOP_K = int(os.getenv("TREE_RAG_TOP_K", "6"))
TREE_RAG_ENABLED = os.getenv("TREE_RAG_ENABLED", "1") == "1"
TREE_LLM_DEDUP = os.getenv("TREE_LLM_DEDUP", "1") == "1"
TREE_LLM_DEDUP_MIN_ITEMS = int(os.getenv("TREE_LLM_DEDUP_MIN_ITEMS", "8"))
TREE_LLM_DEDUP_MAX_ITEMS = int(os.getenv("TREE_LLM_DEDUP_MAX_ITEMS", "40"))
TREE_DEDUP_CROSS_SECTION_POINTS = os.getenv("TREE_DEDUP_CROSS_SECTION_POINTS", "1") == "1"
KIMI_MAX_RETRIES = int(os.getenv("KIMI_MAX_RETRIES", "3"))
KIMI_RETRY_BASE_SEC = float(os.getenv("KIMI_RETRY_BASE_SEC", "1.0"))
KIMI_RETRY_MAX_SEC = float(os.getenv("KIMI_RETRY_MAX_SEC", "6.0"))


def _get_db():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB_NAME]


def _materials_col(db):
    return db["materials"]


def _material_texts_col(db):
    return db["material_texts"]


def _knowledge_nodes_col(db):
    return db["knowledge_nodes"]


def _split_text(text: str, max_chars: int = 2000) -> List[str]:
    text = text.strip()
    if not text:
        return []
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]



def _zhipu_post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not ZHIPU_API_KEY:
        raise RuntimeError("ZHIPU_API_KEY is not set")
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _zhipu_chat(messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.2) -> str:
    payload = {
        "model": model or ZHIPU_SUMMARY_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    last_err: Optional[Exception] = None
    for attempt in range(1, TREE_COMPRESS_RETRY_MAX + 1):
        try:
            resp = _zhipu_post_json(ZHIPU_CHAT_URL, payload)
            if isinstance(resp, dict):
                choices = resp.get("choices")
                if isinstance(choices, list) and choices:
                    msg = choices[0].get("message") or {}
                    content = msg.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
                # Some Zhipu responses may use "data" field
                data = resp.get("data")
                if isinstance(data, dict) and isinstance(data.get("choices"), list) and data["choices"]:
                    msg = data["choices"][0].get("message") or {}
                    content = msg.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
            raise RuntimeError(f"Unexpected Zhipu response: {resp}")
        except Exception as exc:
            last_err = exc
            time.sleep(min(1.0 * (2 ** (attempt - 1)), 6.0))
    raise RuntimeError(f"Zhipu chat failed after retries: {last_err}")


def _compress_tree_context(text: str) -> str:
    """Compress long material text into a short outline for knowledge-tree prompting."""
    if not text:
        return ""
    if not TREE_COMPRESS_ENABLED or not ZHIPU_API_KEY:
        # Fallback: balanced excerpt (still capped) to avoid blowing token budget
        return _balanced_excerpt(text, TREE_COMPRESS_MAX_CHARS)

    # Map: summarize each chunk into a compact outline (chapter/section/concepts)
    chunks = _split_text(text, max_chars=TREE_COMPRESS_CHUNK_CHARS)
    outlines: List[str] = []
    for idx, ch in enumerate(chunks):
        prompt = (
            "你是目录/知识结构压缩器。请从以下材料片段中提取可能的：章标题、小节标题、核心概念词。\n"
            "要求：\n"
            "1) 只输出精简的层级大纲（可用 1./1.1/• 形式），不写解释。\n"
            "2) 不要编造；出现就写，不确定就略过。\n"
            "3) 每行尽量短（<=20字），总行数尽量少。\n"
            f"片段索引：{idx+1}/{len(chunks)}\n"
            "材料片段：\n"
            f"{ch}\n"
        )
        out = _zhipu_chat(
            [
                {"role": "system", "content": "你擅长把长文档压缩成可用于目录抽取的短大纲。"},
                {"role": "user", "content": prompt},
            ],
            model=ZHIPU_SUMMARY_MODEL,
            temperature=0.2,
        )
        outlines.append(out)

    merged = "\n".join(outlines).strip()
    if len(merged) <= TREE_COMPRESS_MAX_CHARS:
        return merged

    # Reduce: merge outlines into a final concise outline within max chars
    reduce_prompt = (
        "请把下面多个片段大纲合并去重，生成一个最终精简大纲，用于后续生成知识树。\n"
        "要求：\n"
        "1) 只输出大纲，不写解释。\n"
        "2) 三层结构：章 -> 小节 -> 概念词。\n"
        f"3) 总长度控制在 {TREE_COMPRESS_MAX_CHARS} 字以内。\n"
        "大纲集合：\n"
        f"{merged}\n"
    )
    final = _zhipu_chat(
        [
            {"role": "system", "content": "你擅长合并去重并压缩目录结构。"},
            {"role": "user", "content": reduce_prompt},
        ],
        model=ZHIPU_SUMMARY_MODEL,
        temperature=0.2,
    )
    return final[:TREE_COMPRESS_MAX_CHARS].strip()
def _download_to_temp(url: str) -> Path:
    suffix = Path(url).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
        urllib.request.urlretrieve(url, fp.name)
        return Path(fp.name)


def _resolve_file_path(file_url: str) -> Path:
    if file_url.startswith("http://") or file_url.startswith("https://"):
        return _download_to_temp(file_url)
    return Path(file_url)


def _extract_text_with_kimi(file_path: Path) -> str:
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise RuntimeError("MOONSHOT_API_KEY is required for pdf/docx ingest")
    client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")
    last_exc: Exception | None = None
    for attempt in range(1, KIMI_MAX_RETRIES + 1):
        try:
            file_object = client.files.create(file=file_path, purpose="file-extract")
            return client.files.content(file_id=file_object.id).text
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit_error(exc) and attempt < KIMI_MAX_RETRIES:
                _sleep_with_backoff(attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("Kimi file extract failed")


def _extract_text_with_groq(file_path: Path) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is required for audio ingest")
    client = Groq(api_key=api_key)
    with file_path.open("rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(file_path.name, file.read()),
            model="whisper-large-v3",
            temperature=0,
            response_format="verbose_json",
        )
    return transcription.text


def _call_kimi_chat(prompt: str, system: str) -> str:
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise RuntimeError("MOONSHOT_API_KEY is required")
    client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")
    last_exc: Exception | None = None
    for attempt in range(1, KIMI_MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=KIMI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit_error(exc) and attempt < KIMI_MAX_RETRIES:
                _sleep_with_backoff(attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("Kimi chat failed")


def _summarize_text(text: str, target_chars: int) -> str:
    chunks = _split_text(text, SUMMARY_CHUNK_CHARS)
    summaries = []
    for idx, chunk in enumerate(chunks, 1):
        prompt = (
            "Summarize the following content into concise bullet points with clear section hints. "
            "Keep it brief (roughly 400-600 chars).\n"
            f"Chunk {idx}/{len(chunks)}:\n{chunk}"
        )
        summaries.append(_call_kimi_chat(prompt, system="You summarize study materials."))
    merged = "\n".join(summaries)
    if len(merged) <= target_chars:
        return merged
    prompt = (
        "Compress the following summary into a structured outline within "
        f"{target_chars} characters.\n"
        f"{merged}"
    )
    return _call_kimi_chat(prompt, system="You summarize study materials.")


def _maybe_build_summary(text: str) -> str:
    if len(text) <= SUMMARY_MAX_CHARS:
        return ""
    try:
        return _summarize_text(text, SUMMARY_MAX_CHARS)
    except Exception as exc:
        print(f"[ingest] summary skipped: {exc}")
        return ""


def _strip_code_fence(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return s


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "rate_limit" in msg or "429" in msg or "too many requests" in msg


def _sleep_with_backoff(attempt: int) -> None:
    delay = min(KIMI_RETRY_BASE_SEC * (2 ** (attempt - 1)), KIMI_RETRY_MAX_SEC)
    time.sleep(delay)


def _extract_heading_candidates(text: str) -> Dict[str, List[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates: Dict[str, List[str]] = {"chapters": [], "sections": [], "points": []}
    seen = set()

    chapter_patterns = [
        r"^第[一二三四五六七八九十0-9]+章",
        r"^Chapter\s*\d+",
        r"^#\s+.+$",
    ]
    section_patterns = [
        r"^第[一二三四五六七八九十0-9]+节",
        r"^\d+\.\d+\s",
        r"^\d+\.\d+\b",
        r"^[一二三四五六七八九十]+、",
        # Roman numerals like "IV. DBSCAN"
        r"^[IVXLCDM]+\.\s+",
        r"^[IVXLCDM]+\.",
        # Markdown headings
        r"^##\s+.+$",
    ]
    point_patterns = [
        r"^\d+\.\d+\.\d+\b",
        r"^（[一二三四五六七八九十0-9]+）",
        r"^\([一二三四五六七八九十0-9]+\)",
        r"^###\s+.+$",
    ]

    def _add(kind: str, line: str) -> None:
        key = f"{kind}:{line}"
        if key in seen:
            return
        seen.add(key)
        candidates[kind].append(line)

    for line in lines:
        if len(line) > 60:
            continue
        for pat in chapter_patterns:
            if re.match(pat, line):
                _add("chapters", line)
                break
        for pat in section_patterns:
            if re.match(pat, line):
                _add("sections", line)
                break
        for pat in point_patterns:
            if re.match(pat, line):
                _add("points", line)
                break

        if (
            len(candidates["chapters"]) >= TREE_CANDIDATE_MAX
            and len(candidates["sections"]) >= TREE_CANDIDATE_MAX
            and len(candidates["points"]) >= TREE_CANDIDATE_MAX
        ):
            break

    return candidates


def _extract_json_array(text: str) -> Optional[str]:
    if not text:
        return None
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _parse_tree_json(raw: str) -> List[Dict]:
    cleaned = _strip_code_fence(raw)
    for candidate in (cleaned, _extract_json_array(cleaned)):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if isinstance(data, list):
            return data
    return []


def _extract_json_object(text: str) -> Optional[str]:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _parse_tree_object(raw: str) -> Optional[Any]:
    cleaned = _strip_code_fence(raw)
    for candidate in (cleaned, _extract_json_object(cleaned)):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if isinstance(data, (dict, list)):
            return data
    return None


def _node_title(node: Dict[str, Any]) -> str:
    for key in ("name", "title", "label"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _flatten_nested_tree(tree_obj: Any) -> List[Dict]:
    if not tree_obj:
        return []

    if isinstance(tree_obj, list):
        chapters = tree_obj
    elif isinstance(tree_obj, dict):
        if isinstance(tree_obj.get("children"), list):
            chapters = tree_obj.get("children") or []
        else:
            chapters = [tree_obj]
    else:
        return []

    flattened: List[Dict[str, Any]] = []
    for ch_idx, ch in enumerate(chapters):
        if not isinstance(ch, dict):
            continue
        ch_title = _node_title(ch)
        if not ch_title:
            continue
        flattened.append({"title": ch_title, "level": 1, "order": ch_idx})
        sections = ch.get("children") if isinstance(ch.get("children"), list) else []
        for sec_idx, sec in enumerate(sections):
            if not isinstance(sec, dict):
                continue
            sec_title = _node_title(sec)
            if not sec_title:
                continue
            flattened.append(
                {
                    "title": sec_title,
                    "level": 2,
                    "order": sec_idx,
                    "parent_order": ch_idx,
                }
            )
            points = sec.get("children") if isinstance(sec.get("children"), list) else []
            for pt_idx, pt in enumerate(points):
                if not isinstance(pt, dict):
                    continue
                pt_title = _node_title(pt)
                if not pt_title:
                    continue
                flattened.append(
                    {
                        "title": pt_title,
                        "level": 3,
                        "order": pt_idx,
                        "parent_order": sec_idx,
                        "parent_parent_order": ch_idx,
                    }
                )
    return flattened


def _normalize_flat_tree(data: Any) -> List[Dict]:
    if not isinstance(data, list):
        return []
    cleaned: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        try:
            level = int(item.get("level"))
            order = int(item.get("order"))
        except Exception:
            continue
        if level not in (1, 2, 3):
            continue
        node = {"title": title, "level": level, "order": order}
        if level == 2:
            if "parent_order" not in item:
                continue
            node["parent_order"] = int(item.get("parent_order"))
        if level == 3:
            if "parent_order" not in item or "parent_parent_order" not in item:
                continue
            node["parent_order"] = int(item.get("parent_order"))
            node["parent_parent_order"] = int(item.get("parent_parent_order"))
        cleaned.append(node)
    return cleaned


def _strip_bullet_prefix(line: str) -> str:
    return re.sub(r"^[-*•\s\d\.\)\(]+", "", line).strip()


def _parse_outline_tree(raw: str) -> List[Dict]:
    if not raw:
        return []
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    tree: List[Dict[str, Any]] = []
    chapter_order = -1
    section_order = -1
    point_order_by_section: Dict[tuple[int, int], int] = {}
    current_ch: Optional[int] = None
    current_sec: Optional[int] = None

    for line in lines:
        text = _strip_bullet_prefix(line)
        if not text:
            continue
        text = text.replace("：", ":")

        chapter_match = re.match(r"^(章节|章|chapter)\s*:\s*(.+)$", text, re.IGNORECASE)
        if chapter_match:
            title = chapter_match.group(2).strip()
            if not title:
                continue
            chapter_order += 1
            current_ch = chapter_order
            current_sec = None
            section_order = -1
            tree.append({"title": title, "level": 1, "order": chapter_order})
            continue

        section_match = re.match(r"^(节|小节|section)\s*:\s*(.+)$", text, re.IGNORECASE)
        if section_match:
            title = section_match.group(2).strip()
            if not title:
                continue
            if current_ch is None:
                chapter_order += 1
                current_ch = chapter_order
                tree.append({"title": "未命名章节", "level": 1, "order": chapter_order})
            section_order += 1
            current_sec = section_order
            tree.append(
                {"title": title, "level": 2, "order": section_order, "parent_order": current_ch}
            )
            continue

        point_match = re.match(r"^(知识点|knowledge points?|kp)\s*:\s*(.+)$", text, re.IGNORECASE)
        if point_match:
            title = point_match.group(2).strip()
            if not title:
                continue
            title = re.split(r"[（(]", title)[0].strip()
            if not title:
                continue
            if current_ch is None:
                chapter_order += 1
                current_ch = chapter_order
                tree.append({"title": "未命名章节", "level": 1, "order": chapter_order})
            if current_sec is None:
                section_order += 1
                current_sec = section_order
                tree.append(
                    {"title": "未命名小节", "level": 2, "order": section_order, "parent_order": current_ch}
                )
            key = (current_ch, current_sec)
            pt_order = point_order_by_section.get(key, 0)
            point_order_by_section[key] = pt_order + 1
            tree.append(
                {
                    "title": title,
                    "level": 3,
                    "order": pt_order,
                    "parent_order": current_sec,
                    "parent_parent_order": current_ch,
                }
            )
            continue

    return tree


def _strip_heading_prefix(title: str) -> str:
    t = str(title or "").strip()
    if not t:
        return ""
    t = re.sub(r"^第[一二三四五六七八九十0-9]+[章节]\s*", "", t)
    t = re.sub(r"^[一二三四五六七八九十]+、\s*", "", t)
    t = re.sub(r"^\d+(\.\d+)*\s*", "", t)
    t = re.sub(r"^[\(（][一二三四五六七八九十0-9]+[)）]\s*", "", t)
    return t.strip()


def _normalize_title_for_dedupe(title: str) -> str:
    base = _strip_heading_prefix(str(title or "")).strip()
    if not base:
        return ""
    for stop in ("的", "与", "及", "和", "在", "对", "于", "中", "以及", "及其"):
        base = base.replace(stop, "")
    base = re.sub(r"[^\w\u4e00-\u9fff]+", "", base).lower()
    return base


def _is_similar_title(a: str, b: str) -> bool:
    """Conservative title similarity to avoid accidentally merging distinct branches."""
    if not a or not b:
        return False
    a = a.strip()
    b = b.strip()
    if a == b:
        return True

    # Normalize for comparison
    na = re.sub(r"\s+", " ", a.lower())
    nb = re.sub(r"\s+", " ", b.lower())

    # Very close match only
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, na, nb).ratio()
    if ratio >= 0.92:
        return True

    # Allow small suffix/prefix differences only when one is short
    if min(len(na), len(nb)) <= 6 and ratio >= 0.88:
        return True
    return False


def _parse_dedupe_groups(raw: str) -> List[Dict[str, Any]]:
    cleaned = _strip_code_fence(raw)
    for candidate in (cleaned, _extract_json_array(cleaned)):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)]
        if isinstance(data, dict):
            for key in ("groups", "items", "result"):
                if isinstance(data.get(key), list):
                    return [d for d in data.get(key) if isinstance(d, dict)]
    return []


def _llm_group_titles(titles: List[str], context: str) -> List[Dict[str, Any]]:
    if not titles:
        return []
    prompt = (
        "你在做目录去重。同一父节点下，合并指向同一概念的标题。\n"
        "只输出 JSON 数组，每个元素格式：{\"canonical\": \"...\", \"variants\": [\"...\"]}。\n"
        "要求：\n"
        "1) canonical 必须来自输入标题。\n"
        "2) 所有输入标题必须且只能出现一次（在 canonical 或 variants 中）。\n"
        "3) 不要生成新标题。\n"
        "4) 不要输出任何解释文字。\n\n"
        f"上下文：{context}\n"
        f"标题列表：{titles}\n"
    )
    raw = _call_kimi_chat(prompt, system="You dedupe titles. Output JSON only.")
    groups = _parse_dedupe_groups(raw)
    if groups:
        return groups
    repair_prompt = (
        "把下面内容修复为【合法 JSON 数组】，且只输出 JSON。\n"
        "数组元素格式：{\"canonical\": \"...\", \"variants\": [\"...\"]}。\n"
        f"原始输出：\n{raw}"
    )
    fixed = _call_kimi_chat(repair_prompt, system="You fix invalid JSON. Output JSON only.")
    return _parse_dedupe_groups(fixed)


def _apply_llm_dedupe(children: List[Dict[str, Any]], context: str) -> List[Dict[str, Any]]:
    if not TREE_LLM_DEDUP or not children or not os.getenv("MOONSHOT_API_KEY"):
        return children
    titles = [str(c.get("title") or "").strip() for c in children if str(c.get("title") or "").strip()]
    if len(titles) < TREE_LLM_DEDUP_MIN_ITEMS or len(titles) > TREE_LLM_DEDUP_MAX_ITEMS:
        return children
    groups = _llm_group_titles(titles, context)
    if not groups:
        return children

    node_by_key: Dict[str, Dict[str, Any]] = {}
    for child in children:
        key = _normalize_title_for_dedupe(child.get("title", ""))
        if key and key not in node_by_key:
            node_by_key[key] = child

    group_keys: List[Dict[str, Any]] = []
    for group in groups:
        canonical = str(group.get("canonical") or "").strip()
        variants = [str(v).strip() for v in group.get("variants") or [] if str(v).strip()]
        if not canonical and not variants:
            continue
        keys = [_normalize_title_for_dedupe(canonical)] if canonical else []
        keys.extend([_normalize_title_for_dedupe(v) for v in variants])
        keys = [k for k in keys if k]
        if not keys:
            continue
        group_keys.append({"keys": keys, "canonical_key": keys[0]})

    if not group_keys:
        return children

    used = set()
    merged_children: List[Dict[str, Any]] = []
    for child in children:
        key = _normalize_title_for_dedupe(child.get("title", ""))
        if not key:
            continue
        group = None
        for g in group_keys:
            if any(_is_similar_title(key, k) for k in g["keys"]):
                group = g
                break
        if not group:
            if key in used:
                continue
            used.add(key)
            merged_children.append(child)
            continue

        canonical_key = group["canonical_key"]
        canonical_node = node_by_key.get(canonical_key)
        if not canonical_node:
            canonical_node = child
            node_by_key[canonical_key] = canonical_node
        if canonical_key not in used:
            used.add(canonical_key)
            merged_children.append(canonical_node)
        if child is not canonical_node:
            canonical_node["children"].extend(child.get("children", []))

    return merged_children


def _dedupe_points_across_sections_with_llm(chapter: Dict[str, Any]) -> None:
    if not TREE_LLM_DEDUP or not chapter:
        return
    sections = chapter.get("children") or []
    points: List[Dict[str, Any]] = []
    titles: List[str] = []
    for sec in sections:
        for pt in sec.get("children", []):
            title = str(pt.get("title") or "").strip()
            if not title:
                continue
            points.append({"section": sec, "point": pt})
            titles.append(title)
    if len(titles) < TREE_LLM_DEDUP_MIN_ITEMS or len(titles) > TREE_LLM_DEDUP_MAX_ITEMS:
        return
    groups = _llm_group_titles(titles, context=f"{chapter.get('title', '')} 知识点去重")
    if not groups:
        return

    canonical_map: Dict[str, str] = {}
    for group in groups:
        canonical = str(group.get("canonical") or "").strip()
        variants = [str(v).strip() for v in group.get("variants") or [] if str(v).strip()]
        if not canonical and not variants:
            continue
        canonical_key = _normalize_title_for_dedupe(canonical)
        if not canonical_key:
            continue
        for title in [canonical] + variants:
            key = _normalize_title_for_dedupe(title)
            if key:
                canonical_map[key] = canonical_key

    if not canonical_map:
        return

    seen = set()
    for sec in sections:
        filtered: List[Dict[str, Any]] = []
        for pt in sec.get("children", []):
            key = _normalize_title_for_dedupe(pt.get("title", ""))
            if not key:
                continue
            group_key = canonical_map.get(key, key)
            if group_key in seen:
                continue
            seen.add(group_key)
            filtered.append(pt)
        sec["children"] = filtered
    chapter["children"] = [sec for sec in sections if sec.get("children")]


def _dedupe_tree(tree: List[Dict]) -> List[Dict]:
    if not tree:
        return tree

    chapters = [item for item in tree if int(item.get("level", 0)) == 1]
    sections = [item for item in tree if int(item.get("level", 0)) == 2]
    points = [item for item in tree if int(item.get("level", 0)) == 3]

    chapters = sorted(chapters, key=lambda x: int(x.get("order", 0)))
    sections = sorted(sections, key=lambda x: int(x.get("order", 0)))
    points = sorted(points, key=lambda x: int(x.get("order", 0)))

    chapter_nodes: List[Dict[str, Any]] = []
    chapter_by_order: Dict[int, Dict[str, Any]] = {}
    for ch in chapters:
        order = int(ch.get("order", 0))
        node = {"title": ch.get("title", ""), "order": order, "children": []}
        chapter_nodes.append(node)
        chapter_by_order[order] = node

    section_nodes: Dict[tuple[int, int], Dict[str, Any]] = {}
    for sec in sections:
        parent_order = int(sec.get("parent_order", 0))
        parent = chapter_by_order.get(parent_order)
        if not parent:
            continue
        order = int(sec.get("order", 0))
        node = {"title": sec.get("title", ""), "order": order, "children": []}
        parent["children"].append(node)
        section_nodes[(parent_order, order)] = node

    for pt in points:
        parent_order = int(pt.get("parent_order", 0))
        parent_parent_order = int(pt.get("parent_parent_order", 0))
        parent = section_nodes.get((parent_parent_order, parent_order))
        if not parent:
            continue
        order = int(pt.get("order", 0))
        node = {"title": pt.get("title", ""), "order": order, "children": []}
        parent["children"].append(node)

    def _dedupe_children(children: List[Dict[str, Any]], context: str) -> List[Dict[str, Any]]:
        seen: Dict[str, Dict[str, Any]] = {}
        deduped: List[Dict[str, Any]] = []
        for child in sorted(children, key=lambda x: int(x.get("order", 0))):
            key = _normalize_title_for_dedupe(child.get("title", ""))
            if not key:
                continue
            matched_key = None
            for existing_key in seen:
                if _is_similar_title(existing_key, key):
                    matched_key = existing_key
                    break
            if matched_key:
                seen[matched_key]["children"].extend(child.get("children", []))
            else:
                seen[key] = child
                deduped.append(child)
        deduped = _apply_llm_dedupe(deduped, context)
        for idx, child in enumerate(deduped):
            child["order"] = idx
            child_context = f"{context} / {child.get('title', '')}".strip()
            child["children"] = _dedupe_children(child.get("children", []), child_context)
        return deduped

    chapter_nodes = _dedupe_children(chapter_nodes, context="目录")
    if TREE_DEDUP_CROSS_SECTION_POINTS:
        for ch in chapter_nodes:
            if TREE_LLM_DEDUP:
                _dedupe_points_across_sections_with_llm(ch)
            seen_points: List[str] = []
            for sec in ch.get("children", []):
                filtered_points: List[Dict[str, Any]] = []
                for pt in sec.get("children", []):
                    key = _normalize_title_for_dedupe(pt.get("title", ""))
                    if not key:
                        continue
                    if any(_is_similar_title(key, seen_key) for seen_key in seen_points):
                        continue
                    seen_points.append(key)
                    filtered_points.append(pt)
                sec["children"] = filtered_points
            ch["children"] = [sec for sec in ch.get("children", []) if sec.get("children")]

    def _reindex_nodes(nodes: List[Dict[str, Any]]) -> None:
        for idx, node in enumerate(nodes):
            node["order"] = idx
            if isinstance(node.get("children"), list):
                _reindex_nodes(node["children"])

    if TREE_STAGE_CHAPTER_MAX > 0:
        chapter_nodes = chapter_nodes[:TREE_STAGE_CHAPTER_MAX]
    for ch in chapter_nodes:
        if TREE_STAGE_SECTION_MAX > 0:
            ch["children"] = ch.get("children", [])[:TREE_STAGE_SECTION_MAX]
        for sec in ch.get("children", []):
            if TREE_STAGE_POINT_MAX > 0:
                sec["children"] = sec.get("children", [])[:TREE_STAGE_POINT_MAX]
    _reindex_nodes(chapter_nodes)

    flattened: List[Dict[str, Any]] = []
    for ch in chapter_nodes:
        flattened.append({"title": ch["title"], "level": 1, "order": ch["order"]})
        for sec in ch.get("children", []):
            flattened.append(
                {
                    "title": sec["title"],
                    "level": 2,
                    "order": sec["order"],
                    "parent_order": ch["order"],
                }
            )
            for pt in sec.get("children", []):
                flattened.append(
                    {
                        "title": pt["title"],
                        "level": 3,
                        "order": pt["order"],
                        "parent_order": sec["order"],
                        "parent_parent_order": ch["order"],
                    }
                )
    return flattened


def _clean_redundant_lines(text: str) -> str:
    if not text:
        return text
    lines = [line.strip() for line in text.splitlines()]
    if not lines:
        return text

    def _normalize_line(line: str) -> str:
        cleaned = re.sub(r"\s+", " ", line).strip().lower()
        cleaned = re.sub(r"\d+", "", cleaned)
        return cleaned

    def _looks_like_heading(line: str) -> bool:
        if not line or len(line) > 80:
            return False
        patterns = [
            r"^第[一二三四五六七八九十0-9]+章",
            r"^第[一二三四五六七八九十0-9]+节",
            r"^Chapter\s*\d+",
            r"^\d+\.\d+(\.\d+)?\b",
            r"^[一二三四五六七八九十]+、",
            r"^[IVXLCDM]+\.",
            r"^#+\s+.+$",
        ]
        return any(re.match(pat, line) for pat in patterns)

    counts: Dict[str, int] = {}
    for line in lines:
        key = _normalize_line(line)
        if not key or len(line) > 120:
            continue
        counts[key] = counts.get(key, 0) + 1

    repeated = {key for key, cnt in counts.items() if cnt >= 3}
    if not repeated:
        return text

    cleaned_lines: List[str] = []
    for line in lines:
        key = _normalize_line(line)
        if key in repeated and not _looks_like_heading(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _fallback_tree_from_candidates(candidates: Dict[str, List[str]]) -> List[Dict]:
    chapters = [c for c in (candidates.get("chapters") or []) if str(c).strip()]
    sections = [s for s in (candidates.get("sections") or []) if str(s).strip()]
    points = [p for p in (candidates.get("points") or []) if str(p).strip()]

    if not chapters:
        chapters = ["课程内容"]

    tree: List[Dict] = []
    chapter_count = min(len(chapters), TREE_CANDIDATE_MAX)

    for idx, title in enumerate(chapters[:chapter_count]):
        tree.append({"title": str(title).strip(), "level": 1, "order": idx})

    section_nodes: List[Dict[str, Any]] = []
    section_order_by_chapter: Dict[int, int] = {}
    if sections:
        for idx, title in enumerate(sections[: TREE_CANDIDATE_MAX * 2]):
            chapter_order = idx % chapter_count
            sec_order = section_order_by_chapter.get(chapter_order, 0)
            section_order_by_chapter[chapter_order] = sec_order + 1
            sec_title = str(title).strip()
            tree.append(
                {
                    "title": sec_title,
                    "level": 2,
                    "order": sec_order,
                    "parent_order": chapter_order,
                }
            )
            section_nodes.append(
                {"title": sec_title, "order": sec_order, "parent_order": chapter_order}
            )
    else:
        for ch_order, ch in enumerate(chapters[:chapter_count]):
            base = _strip_heading_prefix(ch) or str(ch).strip()
            for sec_order in range(2):
                sec_title = f"{base} 小节{sec_order + 1}"
                tree.append(
                    {
                        "title": sec_title,
                        "level": 2,
                        "order": sec_order,
                        "parent_order": ch_order,
                    }
                )
                section_nodes.append(
                    {"title": sec_title, "order": sec_order, "parent_order": ch_order}
                )

    if not section_nodes:
        return tree

    point_order: Dict[tuple[int, int], int] = {}
    if points:
        for idx, title in enumerate(points[: TREE_CANDIDATE_MAX * 4]):
            sec = section_nodes[idx % len(section_nodes)]
            key = (sec["parent_order"], sec["order"])
            pt_order = point_order.get(key, 0)
            point_order[key] = pt_order + 1
            tree.append(
                {
                    "title": str(title).strip(),
                    "level": 3,
                    "order": pt_order,
                    "parent_order": sec["order"],
                    "parent_parent_order": sec["parent_order"],
                }
            )
    else:
        for sec in section_nodes:
            key = (sec["parent_order"], sec["order"])
            base = _strip_heading_prefix(sec["title"]) or sec["title"]
            tree.append(
                {
                    "title": f"{base} 关键概念",
                    "level": 3,
                    "order": point_order.get(key, 0),
                    "parent_order": sec["order"],
                    "parent_parent_order": sec["parent_order"],
                }
            )
            point_order[key] = point_order.get(key, 0) + 1

    return tree


def _normalize_heading(title: str) -> str:
    if not title:
        return ""
    stripped = _strip_heading_prefix(str(title))
    return re.sub(r"\s+", "", stripped).lower()


def _dedupe_titles(titles: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in titles:
        title = str(item).strip()
        if not title:
            continue
        key = _normalize_title_for_dedupe(title) or title
        if key in seen:
            continue
        seen.add(key)
        result.append(title)
    return result


def _limit_context(text: str, max_chars: int) -> str:
    return text.strip()[:max_chars] if text else ""

def _balanced_excerpt(text: str, max_chars: int) -> str:
    """Return a head+tail excerpt so late-section topics aren't dropped by truncation."""
    if not text:
        return ""
    src = text.strip()
    if len(src) <= max_chars:
        return src
    half = max_chars // 2
    return src[:half] + "\n...\n" + src[-half:]



def _parse_title_list(raw: str) -> List[str]:
    cleaned = _strip_code_fence(raw)
    for candidate in (cleaned, _extract_json_array(cleaned)):
        if not candidate:
            continue
        try:
            data: Any = json.loads(candidate)
        except Exception:
            continue
        items: Optional[List[Any]] = None
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ("items", "chapters", "sections", "points", "knowledge_points"):
                if isinstance(data.get(key), list):
                    items = data.get(key)
                    break
        if not items:
            continue
        titles: List[str] = []
        for item in items:
            if isinstance(item, str):
                title = item
            elif isinstance(item, dict):
                title = item.get("title") or item.get("name")
            else:
                continue
            if title:
                titles.append(str(title).strip())
        if titles:
            return titles
    return []


def _call_kimi_json_list(prompt: str, system: str, kind: str) -> List[str]:
    raw = _call_kimi_chat(prompt, system=system)
    titles = _parse_title_list(raw)
    if titles:
        return _dedupe_titles(titles)
    repair_prompt = (
        "请把下面内容修复为【合法 JSON 数组】且只输出 JSON。\n"
        f"数组元素必须是 {kind} 标题字符串。\n"
        f"原始输出：\n{raw}"
    )
    fixed = _call_kimi_chat(repair_prompt, system="You fix invalid JSON. Output JSON only.")
    return _dedupe_titles(_parse_title_list(fixed))


def _extract_query_terms(query: str) -> List[str]:
    cleaned = _strip_heading_prefix(query)
    terms = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", cleaned)
    if cleaned != query:
        terms += re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", query)
    normalized = []
    for term in terms:
        t = str(term).strip().lower()
        if len(t) < 2 and not t.isdigit():
            continue
        normalized.append(t)
    return _dedupe_titles(normalized)[:12]


def _rank_chunks_by_query(chunks: List[str], query: str, top_k: int) -> List[str]:
    if not chunks or not query or top_k <= 0:
        return []
    terms = _extract_query_terms(query)
    if not terms:
        return []
    q_lower = query.lower()
    scored: List[Tuple[int, str]] = []
    for chunk in chunks:
        text = chunk.lower()
        score = 0
        if q_lower and q_lower in text:
            score += 5
        for term in terms:
            if term in text:
                score += 1 + min(text.count(term), 3)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def _build_rag_context(chunks: List[str], query: str, max_chars: int) -> str:
    if not TREE_RAG_ENABLED or TREE_RAG_TOP_K <= 0:
        return ""
    ranked = _rank_chunks_by_query(chunks, query, TREE_RAG_TOP_K)
    if not ranked:
        return ""
    ctx = "\n".join(ranked)
    return ctx  # no truncation per requirement


def _filter_candidates_for_text(candidates: List[str], text: str, limit: int) -> List[str]:
    if not candidates or not text:
        return []
    text_lower = text.lower()
    result: List[str] = []
    for cand in candidates:
        title = str(cand).strip()
        if not title:
            continue
        if title in text or title.lower() in text_lower:
            result.append(title)
        if len(result) >= limit:
            break
    return result


def _build_heading_positions(text: str, candidates: List[str]) -> List[Tuple[int, str]]:
    positions: List[Tuple[int, str]] = []
    if not text:
        return positions
    for cand in candidates:
        title = str(cand).strip()
        if not title:
            continue
        pos = text.find(title)
        if pos >= 0:
            positions.append((pos, title))
    positions.sort(key=lambda x: x[0])
    return positions


def _slice_text_for_heading(text: str, title: str, candidates: List[str]) -> str:
    if not text or not title or not candidates:
        return ""
    positions = _build_heading_positions(text, candidates)
    if not positions:
        return ""
    norm_title = _normalize_heading(title)
    best_idx: Optional[int] = None
    for idx, (_, cand) in enumerate(positions):
        norm_cand = _normalize_heading(cand)
        if not norm_cand:
            continue
        if norm_title in norm_cand or norm_cand in norm_title:
            best_idx = idx
            break
    if best_idx is None:
        return ""
    start = positions[best_idx][0]
    end = positions[best_idx + 1][0] if best_idx + 1 < len(positions) else len(text)
    if end <= start:
        return ""
    return text[start:end]


def _fallback_sections_for_chapter(
    chapter_title: str, chapter_text: str, candidates: List[str]
) -> List[str]:
    sections = _filter_candidates_for_text(candidates, chapter_text, TREE_STAGE_SECTION_MAX)
    if sections:
        return sections
    base = _strip_heading_prefix(chapter_title) or chapter_title
    return [f"{base} 小节{i + 1}" for i in range(2)]


def _fallback_points_for_section(
    section_title: str, section_text: str, candidates: List[str]
) -> List[str]:
    points = _filter_candidates_for_text(candidates, section_text, TREE_STAGE_POINT_MAX)
    if points:
        return points
    base = _strip_heading_prefix(section_title) or section_title
    return [f"{base} 关键概念{i + 1}" for i in range(2)]


def _build_knowledge_tree_staged(
    text: str,
    summary_text: str,
    candidates: Optional[Dict[str, List[str]]] = None,
    chunks: Optional[List[str]] = None,
) -> List[Dict]:
    def _balanced_excerpt(src: str, max_chars: int) -> str:
        if not src:
            return ""
        if len(src) <= max_chars:
            return src
        half = max_chars // 2
        return src[:half] + "\n...\n" + src[-half:]

    # NOTE: summary_text may omit late-section topics (e.g., DBSCAN). For tree completeness,
    # use a balanced excerpt of the full text so both early and late headings can be extracted.
    base_text = _balanced_excerpt(text, TREE_CONTEXT_MAX_CHARS * 2)

    rag_chunks = chunks or _split_text(text)
    chapter_candidates = (candidates or {}).get("chapters") or []
    chapter_ctx = base_text.strip() if base_text else ""  # no truncation per requirement

    prompt = (
        "从以下学习资料中提取【章级目录】。\n"
        "要求：\n"
        "1) 只输出 JSON 数组，数组元素为章节标题字符串。\n"
        "2) 标题简短、像目录，最多 15 章。\n"
        "3) 同一层级标题必须唯一，不要重复。\n"
        "4) 标题必须来源于材料或候选标题，不要编造。\n"
        "5) 避免泛化标题（如：问题定义/基本方法/总结/性质/步骤等），"
        "若必须使用，请加限定（例如：岭回归-问题定义）。\n"
        "6) 不要输出任何解释文字。\n\n"
        f"资料内容：\n{chapter_ctx}\n"
    )
    if chapter_candidates:
        prompt += f"\n候选章标题（优先复用，可精简）：\n{chapter_candidates[:TREE_CANDIDATE_MAX]}\n"

    chapters = _call_kimi_json_list(
        prompt,
        system="You are an information extraction engine. Output JSON only.",
        kind="章节",
    )
    if not chapters and chapter_candidates:
        chapters = chapter_candidates
    chapters = _dedupe_titles(chapters)[:TREE_STAGE_CHAPTER_MAX]
    if not chapters:
        raise ValueError("chapter list is empty")

    tree: List[Dict] = []
    section_candidates = (candidates or {}).get("sections") or []
    point_candidates = (candidates or {}).get("points") or []

    for ch_idx, ch_title in enumerate(chapters):
        tree.append({"title": ch_title, "level": 1, "order": ch_idx})

        chapter_text = _slice_text_for_heading(text, ch_title, chapter_candidates)
        chapter_ctx = _build_rag_context(rag_chunks, ch_title, TREE_CONTEXT_MAX_CHARS)
        if not chapter_ctx:
            if not chapter_text:
                chapter_text = base_text
            chapter_ctx = chapter_text.strip() if chapter_text else ""  # no truncation per requirement
        if not chapter_text:
            chapter_text = base_text
        chapter_section_candidates = _filter_candidates_for_text(
            section_candidates, chapter_text, TREE_STAGE_SECTION_MAX * 2
        )

        sec_prompt = (
            f"为章节《{ch_title}》提取【小节目录】。\n"
            "要求：\n"
            "1) 只输出 JSON 数组，数组元素为小节标题字符串。\n"
            "2) 每章最多 10 节，标题简短。\n"
            "3) 同一章内小节标题必须唯一，不要重复。\n"
            "4) 小节标题必须来源于材料或候选标题，不要编造。\n"
            "5) 避免泛化标题（如：问题定义/基本方法/总结/性质/步骤等），"
            "若必须使用，请加限定（例如：岭回归-问题定义）。\n"
            "6) 不要输出任何解释文字。\n\n"
            f"章节内容：\n{chapter_ctx}\n"
        )
        if chapter_section_candidates:
            sec_prompt += f"\n候选小节标题（优先复用，可精简）：\n{chapter_section_candidates}\n"

        sections = _call_kimi_json_list(
            sec_prompt,
            system="You are an information extraction engine. Output JSON only.",
            kind="小节",
        )
        if not sections:
            sections = chapter_section_candidates
        if not sections:
            sections = _fallback_sections_for_chapter(ch_title, chapter_text, section_candidates)

        sections = _dedupe_titles(sections)[:TREE_STAGE_SECTION_MAX]
        if not sections:
            continue

        for sec_idx, sec_title in enumerate(sections):
            tree.append(
                {
                    "title": sec_title,
                    "level": 2,
                    "order": sec_idx,
                    "parent_order": ch_idx,
                }
            )

            section_text = _slice_text_for_heading(chapter_text, sec_title, section_candidates)
            section_query = f"{ch_title} {sec_title}".strip()
            section_ctx = _build_rag_context(rag_chunks, section_query, TREE_CONTEXT_MAX_CHARS)
            if not section_ctx:
                if not section_text:
                    section_text = chapter_text
                section_ctx = section_text.strip() if section_text else ""  # no truncation per requirement
            if not section_text:
                section_text = chapter_text
            section_point_candidates = _filter_candidates_for_text(
                point_candidates, section_text, TREE_STAGE_POINT_MAX * 2
            )

            pt_prompt = (
                f"为小节《{sec_title}》提取【知识点】。\n"
                "要求：\n"
                "1) 只输出 JSON 数组，数组元素为知识点标题字符串。\n"
                "2) 每节最多 10 个知识点，标题简短（2-12 字/词）。\n"
                "3) 同一小节内知识点必须唯一，不要重复。\n"
                "4) 知识点必须来源于材料，不要编造。\n"
                "5) 避免泛化标题（如：问题定义/基本方法/总结/性质/步骤等），"
                "若必须使用，请加限定（例如：岭回归-问题定义）。\n"
                "6) 不要输出任何解释文字。\n\n"
                f"小节内容：\n{section_ctx}\n"
            )
            if section_point_candidates:
                pt_prompt += f"\n候选知识点（优先复用，可精简）：\n{section_point_candidates}\n"

            points = _call_kimi_json_list(
                pt_prompt,
                system="You are an information extraction engine. Output JSON only.",
                kind="知识点",
            )
            if not points:
                points = section_point_candidates
            if not points:
                points = _fallback_points_for_section(sec_title, section_text, point_candidates)

            points = _dedupe_titles(points)[:TREE_STAGE_POINT_MAX]
            if not points:
                continue

            for pt_idx, pt_title in enumerate(points):
                tree.append(
                    {
                        "title": pt_title,
                        "level": 3,
                        "order": pt_idx,
                        "parent_order": sec_idx,
                        "parent_parent_order": ch_idx,
                    }
                )

    tree = _dedupe_tree(tree)
    if not any(item.get("level") == 3 for item in tree):
        raise ValueError("knowledge tree missing level 3 nodes")
    return tree


def _build_knowledge_tree(text: str, candidates: Optional[Dict[str, List[str]]] = None) -> List[Dict]:
    """
    M2：生成章/节/知识点树（level=1/2/3），输出 JSON 数组：
    [
      {"title":"第1章 ...","level":1,"order":0},
      {"title":"1.1 ...","level":2,"order":0,"parent_order":0},
      {"title":"知识点A","level":3,"order":0,"parent_order":0,"parent_parent_order":0}
    ]
    """
    ctx = _compress_tree_context(text.strip() if text else "")  # compressed to avoid token limit
    if len(ctx) > TREE_CONTEXT_MAX_CHARS:
        ctx = _balanced_excerpt(ctx, TREE_CONTEXT_MAX_CHARS)
    candidate_block = ""
    if candidates:
        ch_titles = _dedupe_titles(candidates.get("chapters") or [])[:TREE_CANDIDATE_MAX]
        sec_titles = _dedupe_titles(candidates.get("sections") or [])[:TREE_CANDIDATE_MAX]
        pt_titles = _dedupe_titles(candidates.get("points") or [])[:TREE_CANDIDATE_MAX]
        lines = []
        if ch_titles:
            lines.append(f"章节候选: {', '.join(ch_titles)}")
        if sec_titles:
            lines.append(f"小节候选: {', '.join(sec_titles)}")
        if pt_titles:
            lines.append(f"知识点候选: {', '.join(pt_titles)}")
        if lines:
            candidate_block = "\n候选标题（优先复用，不可编造）：\n" + "\n".join(lines)

    prompt = (
        "你是一个知识结构抽取引擎。请从材料中构建 JSON 知识树。\n"
        "只输出 JSON 字符串，不要任何解释或 Markdown。\n"
        "必须是三层：章节 -> 小节 -> 知识点。\n"
        "字段要求：name, value, level, mastery, children。\n"
        "level 只能是 chapter/section/concept；mastery 固定为 0；value 不超过 50 字。\n"
        f"数量限制：最多 {TREE_STAGE_CHAPTER_MAX} 章；每章最多 {TREE_STAGE_SECTION_MAX} 节；"
        f"每节最多 {TREE_STAGE_POINT_MAX} 个知识点。\n"
        "标题必须来自材料或候选标题，同一父节点下禁止重复；不要编造。\n"
        "输出示例（仅结构示意）：\n"
        "{\"name\":\"文档标题\",\"level\":\"root\",\"mastery\":0,\"value\":\"\",\"children\":["
        "{\"name\":\"第1章\",\"level\":\"chapter\",\"mastery\":0,\"value\":\"...\",\"children\":["
        "{\"name\":\"1.1 ...\",\"level\":\"section\",\"mastery\":0,\"value\":\"...\",\"children\":["
        "{\"name\":\"知识点A\",\"level\":\"concept\",\"mastery\":0,\"value\":\"...\",\"children\":[]}"
        "]}]}]}\n"
        f"{candidate_block}\n"
        f"材料内容：\n{ctx}\n"
    )
    raw = _call_kimi_chat(prompt, system="You are an information extraction engine. Output JSON only.")
    data: List[Dict[str, Any]] = []
    tree_obj = _parse_tree_object(raw)
    if tree_obj is not None:
        if isinstance(tree_obj, list) and tree_obj and all(
            isinstance(it, dict) and "level" in it for it in tree_obj
        ):
            data = _normalize_flat_tree(tree_obj)
        elif isinstance(tree_obj, dict) and "level" in tree_obj and "children" not in tree_obj:
            data = _normalize_flat_tree([tree_obj])
        else:
            data = _flatten_nested_tree(tree_obj)

    if not data:
        outline_prompt = (
            "从以下材料中提取出知识体系结构，按以下层级输出：\n"
            "1. 章节（Chapter）：每个章节的标题及其包含的节（Section）。\n"
            "2. 小节（Section）：每个节的标题及其包含的知识点（Knowledge Points）。\n"
            "3. 知识点（Knowledge Points）：每个节下的具体知识点，提供简短描述。\n\n"
            "请按照以下格式输出：\n"
            "- 章节: {章节标题}\n"
            "  - 节: {节标题}\n"
            "    - 知识点: {知识点标题} （简短描述）\n\n"
            "确保：\n"
            "- 每个章节、节、知识点是唯一的。\n"
            "- 如果章节中有多个节，确保每个节标题和内容不重复。\n"
            "- 对于每个节，列出该节下的所有知识点，确保清晰且没有遗漏。\n\n"
            f"材料内容：\n{ctx}\n"
        )
        raw = _call_kimi_chat(outline_prompt, system="You are an information extraction engine.")
        data = _parse_outline_tree(raw)

    if not data:
        json_prompt = (
            "从以下学习资料中，提取“章节目录结构”。\n"
            "要求：\n"
            "1) 只输出 JSON 数组；不要输出任何解释文字。\n"
            "1.1) 使用双引号，确保 JSON 完全有效。\n"
            "2) 做三层：章(level=1)、节(level=2)、知识点(level=3)。\n"
            "3) 每个对象字段：title(str), level(int), order(int)。\n"
            "   - level=1: 仅 title/level/order。\n"
            "   - level=2: 额外 parent_order(章的 order)。\n"
            "   - level=3: 额外 parent_order(节的 order) 与 parent_parent_order(章的 order)。\n"
            "4) order 从 0 开始递增，且在各自父节点内递增。\n"
            "5) title 必须短且像目录（不要整段句子）。\n"
            f"6) 每章最多 {TREE_STAGE_SECTION_MAX} 节，每节最多 {TREE_STAGE_POINT_MAX} 知识点，"
            f"最多 {TREE_STAGE_CHAPTER_MAX} 章。\n"
            "7) 标题必须来源于材料或候选标题，不要编造。\n"
            "8) 避免泛化标题（如：问题定义/基本方法/总结/性质/步骤等），"
            "若必须使用，请加限定（例如：岭回归-问题定义）。\n"
            "9) 同一父节点下标题必须唯一，不要重复。\n\n"
            f"资料内容：\n{ctx}\n"
        )
        raw = _call_kimi_chat(json_prompt, system="You are an information extraction engine. Output JSON only.")
        data = _normalize_flat_tree(_parse_tree_json(raw))
        if not data:
            repair_prompt = (
                "修复下面的输出为【合法 JSON 数组】并且只输出 JSON，不要解释。\n"
                "保持原有结构字段：title, level, order, parent_order, parent_parent_order。\n"
                f"原始输出：\n{raw}"
            )
            fixed = _call_kimi_chat(repair_prompt, system="You fix invalid JSON. Output JSON only.")
            data = _normalize_flat_tree(_parse_tree_json(fixed))
        if not data and candidates:
            data = _fallback_tree_from_candidates(candidates)
        if not data:
            raise ValueError("knowledge tree must be a JSON array")

    if not data:
        raise ValueError("knowledge tree is empty after validation")
    return _dedupe_tree(data)


def ingest_material(material_id: str):
    db = _get_db()
    materials = _materials_col(db)
    material_texts = _material_texts_col(db)
    knowledge_nodes = _knowledge_nodes_col(db)

    material = materials.find_one({"_id": ObjectId(material_id)})
    if not material:
        print(f"[ingest] material not found: {material_id}")
        return

    materials.update_one({"_id": ObjectId(material_id)}, {"$set": {"status": "processing"}})

    file_url = material.get("file_url")
    source_type = material.get("source_type")
    notebook_id = material.get("notebook_id")
    student_id = material.get("student_id")
    if not file_url:
        materials.update_one(
            {"_id": ObjectId(material_id)},
            {"$set": {"status": "failed", "error_message": "file_url missing"}},
        )
        return

    temp_path: Path | None = None
    try:
        file_path = _resolve_file_path(file_url)
        temp_path = file_path if file_url.startswith("http") else None
        if not file_path.exists():
            raise FileNotFoundError(f"file not found: {file_path}")

        if source_type in {"pdf", "docx"}:
            text = _extract_text_with_kimi(file_path)
        elif source_type == "audio":
            text = _extract_text_with_groq(file_path)
        else:
            raise RuntimeError(f"unsupported source_type: {source_type}")

        chunks = _split_text(text)
        if not chunks:
            raise RuntimeError("extracted text is empty")

        now = datetime.utcnow()
        material_texts.delete_many({"material_id": material_id, "kind": "full"})
        docs = []
        for idx, chunk in enumerate(chunks):
            doc = {
                "material_id": material_id,
                "kind": "full",
                "chunk_index": idx,
                "text": chunk,
                "created_at": now,
            }
            if student_id:
                doc["student_id"] = student_id
            if notebook_id:
                doc["notebook_id"] = notebook_id
            docs.append(doc)
        material_texts.insert_many(docs)

        if RAG_ENABLED:
            try:
                embed_count = build_embeddings(
                    db,
                    material_id,
                    chunks,
                    student_id=student_id,
                    notebook_id=notebook_id,
                )
                if embed_count:
                    print(f"[ingest] embeddings stored: {embed_count}")
            except Exception as exc:
                print(f"[ingest] embeddings skipped: {exc}")

        summary_text = _maybe_build_summary(text)
        summary_count = 0
        if summary_text:
            summary_chunks = _split_text(summary_text)
            if summary_chunks:
                material_texts.delete_many({"material_id": material_id, "kind": "summary"})
                summary_docs = []
                for idx, chunk in enumerate(summary_chunks):
                    doc = {
                        "material_id": material_id,
                        "kind": "summary",
                        "chunk_index": idx,
                        "text": chunk,
                        "created_at": now,
                    }
                    if student_id:
                        doc["student_id"] = student_id
                    if notebook_id:
                        doc["notebook_id"] = notebook_id
                    summary_docs.append(doc)
                material_texts.insert_many(summary_docs)
                summary_count = len(summary_chunks)

        # ---------------- M2 新增：生成知识体系树并入库 ----------------
        # 输入优先用 summary（更像目录提取），没有 summary 就用原文前一段
        tree_text = _clean_redundant_lines(text)
        # NOTE: summary_text can miss late sections (e.g., DBSCAN). Use a head+tail excerpt of the full text.
        base_tree_text = _balanced_excerpt(tree_text, TREE_CONTEXT_MAX_CHARS * 2)
        compressed_tree_text = _compress_tree_context(base_tree_text)
        tree_source = (summary_text.strip() + "\n\n" if summary_text else "") + compressed_tree_text
        tree_candidates = _extract_heading_candidates(tree_text)
        tree_chunks = _split_text(tree_text)
        if not tree_chunks:
            tree_chunks = chunks
        try:
            if TREE_EXTRACT_MODE == "single":
                tree = _build_knowledge_tree(tree_source, tree_candidates)
            else:
                try:
                    tree = _build_knowledge_tree_staged(
                        tree_text, summary_text, tree_candidates, chunks=tree_chunks
                    )
                except Exception as exc:
                    print(f"[ingest] staged tree failed: {exc}")
                    tree = _build_knowledge_tree(tree_source, tree_candidates)
            knowledge_nodes.delete_many({"material_id": material_id})
            chapter_id_by_order: Dict[int, ObjectId] = {}
            section_id_by_key: Dict[tuple[int, int], ObjectId] = {}

            # --- M2 加强：给每个章/节绑定 source_chunk_indexes（用于按知识区域出题）---
            # 这里做一个“可用且稳定”的粗绑定：
            # - 章节点：按章数把全文 chunks 均分成连续区间
            # - 节节点：在所属章区间内再均分
            # - 知识点：在所属节区间内再均分
            num_chunks = len(chunks)
            chapters = sorted([it for it in tree if int(it.get("level", 0)) == 1], key=lambda x: int(x.get("order", 0)))
            chapter_ranges: Dict[int, tuple[int, int]] = {}
            if chapters and num_chunks > 0:
                c = len(chapters)
                for idx, ch in enumerate(chapters):
                    order = int(ch.get("order", idx))
                    start = int((idx * num_chunks) / c)
                    end = int(((idx + 1) * num_chunks) / c) - 1
                    if end < start:
                        end = start
                    chapter_ranges[order] = (start, min(end, num_chunks - 1))

            # 预先整理每个章下的节与知识点
            sections_by_parent: Dict[int, List[Dict]] = {}
            points_by_parent: Dict[tuple[int, int], List[Dict]] = {}
            for it in tree:
                level = int(it.get("level", 0))
                if level == 2:
                    po = int(it.get("parent_order", 0))
                    sections_by_parent.setdefault(po, []).append(it)
                elif level == 3:
                    cpo = int(it.get("parent_parent_order", 0))
                    spo = int(it.get("parent_order", 0))
                    points_by_parent.setdefault((cpo, spo), []).append(it)
            for po, secs in sections_by_parent.items():
                sections_by_parent[po] = sorted(secs, key=lambda x: int(x.get("order", 0)))
            for key, pts in points_by_parent.items():
                points_by_parent[key] = sorted(pts, key=lambda x: int(x.get("order", 0)))

            section_ranges: Dict[tuple[int, int], tuple[int, int]] = {}
            if chapters and num_chunks > 0:
                for ch in chapters:
                    ch_order = int(ch.get("order", 0))
                    rng = chapter_ranges.get(ch_order)
                    secs = sections_by_parent.get(ch_order) or []
                    if not rng or not secs:
                        continue
                    start, end = rng
                    length = end - start + 1
                    s = len(secs)
                    for idx, sec in enumerate(secs):
                        sec_order = int(sec.get("order", idx))
                        sub_start = start + int((idx * length) / s)
                        sub_end = start + int(((idx + 1) * length) / s) - 1
                        if sub_end < sub_start:
                            sub_end = sub_start
                        sub_end = min(sub_end, end)
                        section_ranges[(ch_order, sec_order)] = (sub_start, sub_end)

            point_ranges: Dict[tuple[int, int, int], tuple[int, int]] = {}
            for key, pts in points_by_parent.items():
                rng = section_ranges.get(key)
                if not rng or not pts:
                    continue
                start, end = rng
                length = end - start + 1
                p = len(pts)
                for idx, pt in enumerate(pts):
                    pt_order = int(pt.get("order", idx))
                    sub_start = start + int((idx * length) / p)
                    sub_end = start + int(((idx + 1) * length) / p) - 1
                    if sub_end < sub_start:
                        sub_end = sub_start
                    sub_end = min(sub_end, end)
                    point_ranges[(key[0], key[1], pt_order)] = (sub_start, sub_end)

            inserts = []
            for item in tree:
                level = int(item["level"])
                order = int(item["order"])
                title = str(item["title"]).strip()
                if level == 1:
                    rng = chapter_ranges.get(order)
                    src = list(range(rng[0], rng[1] + 1)) if rng else []
                    doc = {
                        "material_id": material_id,
                        "notebook_id": notebook_id,
                        "parent_id": None,
                        "title": title,
                        "level": 1,
                        "order": order,
                        "source_chunk_indexes": src,
                        "created_at": now,
                    }
                    if student_id:
                        doc["student_id"] = student_id
                    res = knowledge_nodes.insert_one(doc)
                    chapter_id_by_order[order] = res.inserted_id
                elif level == 2:
                    parent_order = int(item.get("parent_order", 0))
                    parent_id = chapter_id_by_order.get(parent_order)

                    # 在章区间内均分节区间
                    src: List[int] = []
                    rng = section_ranges.get((parent_order, order))
                    if rng:
                        src = list(range(rng[0], rng[1] + 1))

                    doc = {
                        "material_id": material_id,
                        "notebook_id": notebook_id,
                        "parent_id": str(parent_id) if parent_id else None,
                        "title": title,
                        "level": 2,
                        "order": order,
                        "source_chunk_indexes": src,
                        "created_at": now,
                    }
                    if student_id:
                        doc["student_id"] = student_id
                    res = knowledge_nodes.insert_one(doc)
                    if parent_id:
                        section_id_by_key[(parent_order, order)] = res.inserted_id
                else:
                    parent_order = int(item.get("parent_order", 0))
                    parent_parent_order = int(item.get("parent_parent_order", 0))
                    parent_id = section_id_by_key.get((parent_parent_order, parent_order))

                    src: List[int] = []
                    rng = point_ranges.get((parent_parent_order, parent_order, order))
                    if rng:
                        src = list(range(rng[0], rng[1] + 1))

                    doc = {
                        "material_id": material_id,
                        "notebook_id": notebook_id,
                        "parent_id": str(parent_id) if parent_id else None,
                        "title": title,
                        "level": 3,
                        "order": order,
                        "source_chunk_indexes": src,
                        "created_at": now,
                    }
                    if student_id:
                        doc["student_id"] = student_id
                    inserts.append(doc)

            if inserts:
                knowledge_nodes.insert_many(inserts)
        except Exception as exc:
            # 不让知识树失败拖死 ingest：M2 允许降级
            print(f"[ingest] knowledge tree skipped: {exc}")

        materials.update_one(
            {"_id": ObjectId(material_id)},
            {"$set": {"status": "ready", "text_chunk_count": len(chunks), "summary_chunk_count": summary_count}},
        )
    except Exception as exc:
        materials.update_one(
            {"_id": ObjectId(material_id)},
            {"$set": {"status": "failed", "error_message": str(exc)}},
        )
        print(f"[ingest] failed: {exc}")
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
