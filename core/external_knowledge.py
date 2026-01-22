"""外部知识工具：多源外部搜索。

为了提高在技术类 PPT 场景下的实用性，本模块支持从多个来源检索外部知识片段：

- arXiv：用于检索论文摘要和技术背景
- Wikipedia：作为补充来源
- 百度百科：作为补充来源

注意：这些来源均为在线请求；如网络不可达，本模块会返回空列表，保证主链路可运行。
"""

from __future__ import annotations

from typing import List
from urllib.parse import quote
import re
import xml.etree.ElementTree as ET

import requests

DEFAULT_EXTERNAL_SOURCE = "arxiv"

WIKIPEDIA_API_URL = "https://zh.wikipedia.org/w/api.php"
BAIDU_BAIKE_SEARCH_URL = "https://baike.baidu.com/search/word?word={word}"
ARXIV_API_URL = "http://export.arxiv.org/api/query"


def _strip_html(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    t = re.sub(r"<style[\s\S]*?</style>", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t



def search_wikipedia(query: str, max_results: int = 5) -> List[str]:
    """使用 Wikipedia 的公开 API 搜索条目并返回简介片段列表。"""

    if not query.strip():
        return []

    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": max_results,
        "utf8": 1,
    }

    try:
        resp = requests.get(
            WIKIPEDIA_API_URL,
            params=params,
            timeout=10,
            headers={"User-Agent": "ppt-agent/0.1"},
        )
        resp.raise_for_status()
    except Exception:
        return []

    data = resp.json()
    results = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        snippet_clean = (
            snippet.replace("<span class=\"searchmatch\">", "")
            .replace("</span>", "")
            .replace("<", " ")
            .replace(">", " ")
        )
        results.append(f"【{title}】{snippet_clean}")

    return results


def search_arxiv(query: str, max_results: int = 5) -> List[str]:
    """从 arXiv API 搜索论文，返回标题+摘要片段。"""

    if not query.strip():
        return []

    params = {
        "search_query": f"all:{query.strip()}",
        "start": 0,
        "max_results": max_results,
    }

    try:
        resp = requests.get(ARXIV_API_URL, params=params, timeout=10, headers={"User-Agent": "ppt-agent/0.1"})
        resp.raise_for_status()
    except Exception:
        return []

    try:
        root = ET.fromstring(resp.text)
    except Exception:
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
    }
    results: List[str] = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        title = (title_el.text or "").strip() if title_el is not None else ""
        summary = (summary_el.text or "").strip() if summary_el is not None else ""
        title = re.sub(r"\s+", " ", title)
        summary = re.sub(r"\s+", " ", summary)
        if title or summary:
            results.append(f"【arXiv: {title}】{summary[:500]}")

    return results


def search_baidu_baike(query: str, max_results: int = 5) -> List[str]:
    """从百度百科抓取条目摘要片段。

实现策略：
- 通过搜索入口 /search/word 获取最终条目页面（通常会跳转到 /item/...）；
- 优先读取 <meta name="description"> 作为摘要，兜底从页面文本截取。
"""

    if not query.strip():
        return []

    url = BAIDU_BAIKE_SEARCH_URL.format(word=quote(query.strip()))
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True, headers={"User-Agent": "ppt-agent/0.1"})
        resp.raise_for_status()
    except Exception:
        return []

    html = resp.text or ""

    title = ""
    m_title = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if m_title:
        title = _strip_html(m_title.group(1))
        title = title.replace("_百度百科", "").strip()

    desc = ""
    m_desc = re.search(
        r"<meta\s+name=\"description\"\s+content=\"(.*?)\"\s*/?>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m_desc:
        desc = _strip_html(m_desc.group(1))
    if not desc:
        desc = _strip_html(html)[:400]

    if not title:
        title = query.strip()

    return [f"【{title}】{desc}"]

def search_external_knowledge(
    query: str,
    max_results: int = 3,
    source: str = DEFAULT_EXTERNAL_SOURCE,
) -> List[str]:
    """统一入口：按来源检索外部知识"""

    src = (source or DEFAULT_EXTERNAL_SOURCE).strip().lower()
    if src in {"baidu", "baidu_baike", "baike"}:
        res = search_baidu_baike(query, max_results=max_results)
        if res:
            return res
        res = search_wikipedia(query, max_results=max_results)
        if res:
            return res
        return search_arxiv(query, max_results=max_results)
    if src in {"wikipedia", "wiki"}:
        return search_wikipedia(query, max_results=max_results)
    if src in {"arxiv"}:
        return search_arxiv(query, max_results=max_results)
    return search_baidu_baike(query, max_results=max_results)
