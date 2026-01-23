from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from defusedxml import ElementTree as ET

from app.config import settings


@dataclass(frozen=True)
class RetrievedPassage:
    source: str  # wikipedia | arxiv | local_kb
    domain: str
    title: str
    snippet: str
    url: str | None = None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def wiki_summary(client: httpx.Client, *, domain: str, query: str) -> list[RetrievedPassage]:
    safe = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(query.strip())
    try:
        r = client.get(safe)
        if r.status_code >= 400:
            return []
        data = r.json()
        extract = (data.get("extract") or "").strip()
        if not extract:
            return []
        url = str((data.get("content_urls") or {}).get("desktop", {}).get("page") or "") or None
        title = str(data.get("title") or query)
        return [RetrievedPassage(source="wikipedia", domain=domain, title=title, snippet=extract[:500], url=url)]
    except Exception:
        return []


def arxiv_search(client: httpx.Client, *, domain: str, query: str, max_results: int = 2) -> list[RetrievedPassage]:
    # Atom feed
    q = quote(f"all:{query}")
    url = f"http://export.arxiv.org/api/query?search_query={q}&start=0&max_results={max_results}"
    try:
        r = client.get(url, headers={"user-agent": "xkg-agent/0.1"})
        if r.status_code >= 400:
            return []
        root = ET.fromstring(r.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        out: list[RetrievedPassage] = []
        for entry in root.findall("a:entry", ns)[:max_results]:
            title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
            summ = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
            link = (entry.findtext("a:id", default="", namespaces=ns) or "").strip() or None
            if not title or not summ:
                continue
            out.append(RetrievedPassage(source="arxiv", domain=domain, title=f"arXiv: {title}", snippet=summ[:500], url=link))
        return out
    except Exception:
        return []


def local_kb_search(*, domain: str, query: str, max_results: int = 2) -> list[RetrievedPassage]:
    base = settings.local_kb_path
    if not base or not os.path.exists(base):
        return []

    qn = _norm(query)
    out: list[tuple[int, RetrievedPassage]] = []

    for root, _, files in os.walk(base):
        for fn in files:
            if not fn.lower().endswith(".md"):
                continue
            path = os.path.join(root, fn)
            try:
                txt = open(path, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            tnorm = _norm(txt)
            if qn not in tnorm:
                continue
            # score by occurrences
            score = tnorm.count(qn)
            # snippet: first matching line-ish window
            idx = tnorm.find(qn)
            snippet = txt[max(0, idx - 120) : idx + 260].strip().replace("\n\n", "\n")
            rel = os.path.relpath(path, base).replace("\\", "/")
            out.append(
                (
                    score,
                    RetrievedPassage(
                        source="local_kb",
                        domain=domain,
                        title=f"KB: {rel}",
                        snippet=snippet[:500],
                        url=None,
                    ),
                )
            )

    out.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in out[:max_results]]


def multi_retrieve(*, domain: str, queries: list[str], max_per_source: int = 2) -> list[RetrievedPassage]:
    """
    Multi-source retrieval.
    - Wikipedia (ENABLE_WIKI=1)
    - arXiv (ENABLE_ARXIV=1)
    - Local KB (always attempted if LOCAL_KB_PATH exists)
    """
    seen: set[tuple[str, str]] = set()
    out: list[RetrievedPassage] = []

    with httpx.Client(timeout=10.0) as client:
        for q in queries:
            q = str(q).strip()
            if not q:
                continue

            # local kb
            for p in local_kb_search(domain=domain, query=q, max_results=max_per_source):
                key = (p.source, _norm(p.title))
                if key in seen:
                    continue
                seen.add(key)
                out.append(p)

            # wikipedia
            if settings.enable_wiki:
                for p in wiki_summary(client, domain=domain, query=q):
                    key = (p.source, _norm(p.title))
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(p)

            # arxiv
            if settings.enable_arxiv:
                for p in arxiv_search(client, domain=domain, query=q, max_results=max_per_source):
                    key = (p.source, _norm(p.title))
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(p)

    return out


def to_dicts(passages: list[RetrievedPassage]) -> list[dict[str, Any]]:
    return [
        {
            "source": p.source,
            "domain": p.domain,
            "title": p.title,
            "snippet": p.snippet,
            "url": p.url,
        }
        for p in passages
    ]

