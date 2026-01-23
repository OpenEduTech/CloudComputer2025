from __future__ import annotations

import json
from typing import List, Optional

from config import DEFAULT_KEYWORD
from models import NewsItem, SourceType
from search_agent.search_agent import SearchAgent


def _infer_source_type(source: Optional[str], url: Optional[str]) -> SourceType:
    s = (source or "").strip()
    u = (url or "").lower()

    # 粗粒度规则：政府/官方域名 -> official；其余默认 media
    if ".gov.cn" in u or ".edu.cn" in u:
        return SourceType.OFFICIAL
    if any(k in s for k in ("商务部", "工信部", "发改委", "国家统计局", "国务院", "监管", "公告")):
        return SourceType.OFFICIAL
    if any(k in s for k in ("谣言", "传闻", "小道消息")):
        return SourceType.RUMOR
    return SourceType.MEDIA


class ScraperAgent:
    """采集层：将 SearchAgent 的输出转成项目统一的数据模型 NewsItem。"""

    def __init__(
        self,
        *,
        num_rewrites: int = 3,
        tavily_api_key: Optional[str] = None,
        dashscope_api_key: Optional[str] = None,
    ) -> None:
        self.num_rewrites = num_rewrites
        self._agent = SearchAgent(api_key=tavily_api_key, dashscope_api_key=dashscope_api_key)

    def fetch(self, keyword: str) -> List[NewsItem]:
        result = self._agent.run(keyword, self.num_rewrites)
        items = []

        for r in (result or {}).get("items", []) or []:
            title = (r.get("title") or "").strip()
            content = (r.get("content") or "").strip()
            url = r.get("url")
            published_at = r.get("published_at")

            items.append(
                NewsItem(
                    title=title,
                    content=content,
                    source=_infer_source_type(r.get("source"), url),
                    url=url,
                    published_at=published_at,
                )
            )

        return items


