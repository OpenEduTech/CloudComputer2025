from __future__ import annotations

import json
import os
import re
from typing import List, Optional

from config import DATA_DIR, MAX_DECISIONS, MAX_EVIDENCE_PER_DECISION, INCLUDE_DEBUG_FIELDS
from models import NewsItem, ReportSnapshot, SourceType, now_ts, FinalIndustryReport, EvidenceItem


class StorageClient:
    """存储层：将快照写入对象存储（此处用本地文件模拟）。"""

    def __init__(self, base_dir: str = DATA_DIR) -> None:
        self.base_dir = base_dir

        # 新版目录结构（进一步简化）：按行业隔离，避免不同 keyword 的快照互相干扰
        # data/<slug>/raw_snapshots_*.json
        # data/<slug>/final_analysis_*.json
        self.keywords_root = self.base_dir
        os.makedirs(self.keywords_root, exist_ok=True)

        # 兼容旧目录结构（历史遗留）：仅用于读取回退，不再主动创建目录
        self.legacy_raw_dir = os.path.join(self.base_dir, "raw_snapshots")
        self.legacy_final_dir = os.path.join(self.base_dir, "final_reports")

    def _keyword_slug(self, keyword: str) -> str:
        k = (keyword or "").strip()
        if not k:
            return "default"
        # Windows 路径安全：只保留常见字符，其余替换为 _
        slug = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff._-]+", "_", k)
        slug = slug.strip("._-")
        slug = slug or "default"
        # 避免与保留目录名冲突
        if slug in {"raw_snapshots", "final_reports", "keywords"}:
            slug = f"kw_{slug}"
        return slug

    def _keyword_dir(self, keyword: str) -> str:
        slug = self._keyword_slug(keyword)
        root = os.path.join(self.keywords_root, slug)
        os.makedirs(root, exist_ok=True)
        return root

    def list_keywords(self) -> List[str]:
        """列出已调研过的行业（从 keyword 分目录和历史快照中提取）。"""
        keywords: set[str] = set()

        def _scan_keyword_root(root_dir: str) -> None:
            if not os.path.isdir(root_dir):
                return
            for slug in os.listdir(root_dir):
                if slug in {"raw_snapshots", "final_reports", "keywords"}:
                    continue
                # 1) 新结构：data/<slug>/report_*.json
                root = os.path.join(root_dir, slug)
                if os.path.isdir(root):
                    for fn in os.listdir(root):
                        if not (
                            (fn.startswith("raw_snapshots_") or fn.startswith("report_"))
                            and fn.endswith(".json")
                        ):
                            continue
                        try:
                            with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
                                data = json.load(f)
                            k = (data.get("keyword") or "").strip()
                            if k:
                                keywords.add(k)
                        except Exception:
                            continue

                # 2) 兼容：data/<slug>/raw_snapshots/report_*.json（旧版本）
                legacy_raw = os.path.join(root_dir, slug, "raw_snapshots")
                if os.path.isdir(legacy_raw):
                    for fn in os.listdir(legacy_raw):
                        if not (fn.startswith("report_") and fn.endswith(".json")):
                            continue
                        try:
                            with open(os.path.join(legacy_raw, fn), "r", encoding="utf-8") as f:
                                data = json.load(f)
                            k = (data.get("keyword") or "").strip()
                            if k:
                                keywords.add(k)
                        except Exception:
                            continue

        # 1) 新结构：data/<slug>/...
        _scan_keyword_root(self.keywords_root)

        # 2) 更旧结构兼容：data 根目录 report_*.json
        if os.path.isdir(self.base_dir):
            for fn in os.listdir(self.base_dir):
                if not (
                    (fn.startswith("raw_snapshots_") or fn.startswith("report_"))
                    and fn.endswith(".json")
                ):
                    continue
                try:
                    with open(os.path.join(self.base_dir, fn), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    k = (data.get("keyword") or "").strip()
                    if k:
                        keywords.add(k)
                except Exception:
                    continue

        return sorted(keywords)

    def save_snapshot(self, keyword: str, items: List[NewsItem], collected_at: Optional[str] = None) -> str:
        snapshot = ReportSnapshot(keyword=keyword, collected_at=collected_at or now_ts(), items=items)
        filename = f"raw_snapshots_{snapshot.collected_at}.json"
        root = self._keyword_dir(keyword)
        path = os.path.join(root, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
        return path

    def save_final_report(self, report: FinalIndustryReport) -> str:
        filename = f"final_analysis_{report.generated_at}.json"
        root = self._keyword_dir(report.keyword)
        path = os.path.join(root, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._final_report_to_dict(report), f, ensure_ascii=False, indent=2)
        return path

    def load_latest_snapshot(self, keyword: str) -> Optional[ReportSnapshot]:
        files = self.list_snapshots(keyword)
        if not files:
            return None
        latest = sorted(files)[-1]

        root = self._keyword_dir(keyword)
        path = os.path.join(root, latest)

        # 兼容旧目录：data/raw_snapshots、data 根目录
        if not os.path.isfile(path):
            # 兼容：data/<slug>/raw_snapshots
            slug = self._keyword_slug(keyword)
            legacy_kw_raw = os.path.join(self.base_dir, slug, "raw_snapshots", latest)
            alt1 = os.path.join(self.legacy_raw_dir, latest)
            alt2 = os.path.join(self.base_dir, latest)
            if os.path.isfile(legacy_kw_raw):
                path = legacy_kw_raw
            elif os.path.isfile(alt1):
                path = alt1
            elif os.path.isfile(alt2):
                path = alt2
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._dict_to_snapshot(data)

    def list_snapshots(self, keyword: str) -> List[str]:
        snapshots: List[str] = []

        # 新结构：只列出该 keyword 目录下的快照（无子目录）
        root = self._keyword_dir(keyword)
        if os.path.isdir(root):
            snapshots.extend(
                [
                    f
                    for f in os.listdir(root)
                    if (f.startswith("raw_snapshots_") or f.startswith("report_")) and f.endswith(".json")
                ]
            )
        if snapshots:
            return snapshots

        # 兼容：data/<slug>/raw_snapshots
        slug = self._keyword_slug(keyword)
        legacy_kw_raw_dir = os.path.join(self.base_dir, slug, "raw_snapshots")
        if os.path.isdir(legacy_kw_raw_dir):
            snapshots.extend(
                [f for f in os.listdir(legacy_kw_raw_dir) if f.startswith("report_") and f.endswith(".json")]
            )
        if snapshots:
            return snapshots

        # 旧结构兼容：从旧目录/根目录里筛选 keyword 匹配的快照
        legacy_candidates: List[str] = []
        if os.path.isdir(self.legacy_raw_dir):
            legacy_candidates.extend(
                [f for f in os.listdir(self.legacy_raw_dir) if f.startswith("report_") and f.endswith(".json")]
            )
        if os.path.isdir(self.base_dir):
            legacy_candidates.extend(
                [
                    f
                    for f in os.listdir(self.base_dir)
                    if (f.startswith("raw_snapshots_") or f.startswith("report_")) and f.endswith(".json")
                ]
            )

        for fn in sorted(set(legacy_candidates)):
            # 逐个读取判断 keyword 是否一致
            try:
                p1 = os.path.join(self.legacy_raw_dir, fn)
                p2 = os.path.join(self.base_dir, fn)
                path = p1 if os.path.isfile(p1) else p2
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if (data.get("keyword") or "").strip() == (keyword or "").strip():
                    snapshots.append(fn)
            except Exception:
                continue
        return snapshots

    def _snapshot_to_dict(self, snapshot: ReportSnapshot) -> dict:
        return {
            "keyword": snapshot.keyword,
            "collected_at": snapshot.collected_at,
            "items": [
                {
                    "title": i.title,
                    "content": i.content,
                    "source": i.source.value,
                    "url": i.url,
                    "published_at": i.published_at,
                }
                for i in snapshot.items
            ],
        }

    def _dict_to_snapshot(self, data: dict) -> ReportSnapshot:
        def _to_source_type(raw: object) -> SourceType:
            if isinstance(raw, SourceType):
                return raw
            if isinstance(raw, str):
                try:
                    return SourceType(raw)
                except Exception:
                    return SourceType.MEDIA
            return SourceType.MEDIA

        items = [
            NewsItem(
                title=i.get("title", ""),
                content=i.get("content", ""),
                source=_to_source_type(i.get("source", SourceType.MEDIA.value)),
                url=i.get("url"),
                published_at=i.get("published_at"),
            )
            for i in data.get("items", [])
        ]
        return ReportSnapshot(
            keyword=data.get("keyword", ""),
            collected_at=data.get("collected_at", ""),
            items=items,
        )

    def _final_report_to_dict(self, report: FinalIndustryReport) -> dict:
        def _source_to_dict(e: EvidenceItem) -> dict:
            return {
                "title": getattr(e, "title", ""),
                "url": getattr(e, "url", None),
                "source": getattr(getattr(e, "source", None), "value", getattr(e, "source", None)),
                "published_at": getattr(e, "published_at", None),
            }

        def _parse_num(text: str) -> Optional[tuple[float, str]]:
            t = (text or "").strip()
            if not t:
                return None
            # 尝试抓取第一个“像指标”的数字（含单位）
            m = re.search(r"(-?\d+(?:\.\d+)?)\s*(%|nm|纳米|亿元|万亿元|万元|亿|万|元|美元|GWh|GW|MHz|GHz|TB|GB|MB|倍)?", t)
            if not m:
                return None
            try:
                v = float(m.group(1))
            except Exception:
                return None
            unit = m.group(2) or ""
            return v, unit

        def _delta_summary(old_v: str, new_v: str) -> Optional[str]:
            a = _parse_num(old_v)
            b = _parse_num(new_v)
            if not a or not b:
                return None
            (ov, ou), (nv, nu) = a, b
            # 单位不一致就不强行算差
            if ou != nu:
                return f"{old_v} -> {new_v}"
            diff = nv - ov
            if ou == "%":
                # 百分比用百分点
                return f"{old_v} -> {new_v}（{diff:+.2f}pp）"
            # 其它单位给出差值
            return f"{old_v} -> {new_v}（{diff:+.2f}{ou}）"

        # 汇总 sources（title+url 列表），避免每个指标都重复塞 evidence
        seen: set[str] = set()
        sources: List[dict] = []
        for d in report.decisions:
            for e in (getattr(d, "evidence", None) or []):
                title = (getattr(e, "title", "") or "").strip()
                url = (getattr(e, "url", "") or "").strip()
                key = url or title
                if not key or key in seen:
                    continue
                seen.add(key)
                sources.append(_source_to_dict(e))

        evidence_summary = f"证据来源：共{len(sources)}篇，详见 sources（标题+链接清单）。"

        # 按示例格式组织 key 顺序（JSON 输出时更直观）
        return {
            "keyword": report.keyword,
            "generated_at": report.generated_at,
            "global_summary": report.global_summary,
            "raw_sources_count": report.raw_sources_count,

            "decisions": [
                {
                    "field": d.field,
                    "status": getattr(d, "status", "") or "",
                    "old_value": getattr(d, "old_value", "") or "",
                    "value": d.final_value,
                    "change": _delta_summary(getattr(d, "old_value", "") or "", d.final_value),
                    "arbitration": {
                        "chosen_source": getattr(d.chosen_source, "value", d.chosen_source),
                        "pending_sources": [getattr(s, "value", s) for s in (d.pending_sources or [])],
                        "conflicting_values": list(getattr(d, "conflicting_values", []) or []),
                    },
                    # 理由保留一条短句即可（前端可截断）
                    "reason": (d.reason or "").strip(),
                    **({
                        "evidence": [
                            {
                                **_source_to_dict(e),
                                "quote": (getattr(e, "quote", "") or "").strip(),
                                "key_numbers": list(getattr(e, "key_numbers", []) or []),
                                "snippet": getattr(e, "snippet", "") or "",
                            }
                            for e in (getattr(d, "evidence", None) or [])[: MAX_EVIDENCE_PER_DECISION]
                        ]
                    } if INCLUDE_DEBUG_FIELDS else {}),
                    **({"confidence": float(getattr(d, "confidence", 0.0) or 0.0)} if INCLUDE_DEBUG_FIELDS else {}),
                }
                for d in report.decisions[:MAX_DECISIONS]
            ],

            "_notes": {
                "default_compact": "默认精简：每条 decision 不包含 evidence/key_numbers/confidence/snippet",
                "debug_optional": "如设置 INCLUDE_DEBUG_FIELDS=1，将额外包含 decision.confidence 与 decision.evidence(含quote/key_numbers/snippet)",
            },

            "evidence_summary": evidence_summary,
            "sources": sources,
        }
