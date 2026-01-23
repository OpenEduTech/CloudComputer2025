from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class SourceType(str, Enum):
    OFFICIAL = "official"
    MEDIA = "media"
    RUMOR = "rumor"


SOURCE_WEIGHTS = {
    SourceType.OFFICIAL: 1.0,
    SourceType.MEDIA: 0.7,
    SourceType.RUMOR: 0.3,
}


@dataclass
class NewsItem:
    title: str
    content: str
    source: SourceType
    url: Optional[str] = None
    published_at: Optional[str] = None


@dataclass
class ReportSnapshot:
    keyword: str
    collected_at: str
    items: List[NewsItem] = field(default_factory=list)


@dataclass
class EvidenceItem:
    title: str
    url: Optional[str] = None
    source: Optional[SourceType] = None
    published_at: Optional[str] = None
    quote: str = ""  # 尽量短：包含关键数字/结论的原文片段
    key_numbers: List[str] = field(default_factory=list)  # 提取到的关键数字/单位（用于“数字论据”展示）
    snippet: str = ""  # 兼容旧字段：保留，但不再写入长文本


@dataclass
class ChangeItem:
    field: str
    old: str
    new: str
    status: str
    source: SourceType
    insight: str = ""  # 新增：存储 AI 对变动的通俗化解读
    evidence: List[EvidenceItem] = field(default_factory=list)
    confidence: float = 0.0

@dataclass
class ConflictDecision:
    field: str
    final_value: str
    chosen_source: SourceType
    pending_sources: List[SourceType] = field(default_factory=list)
    reason: str = ""  # 这里将存储最终采纳的 insight
    evidence: List[EvidenceItem] = field(default_factory=list)
    old_value: str = ""
    status: str = ""
    confidence: float = 0.0
    conflicting_values: List[str] = field(default_factory=list)  # 其他来源给出的候选值（用于体现冲突与仲裁）


def now_ts() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


@dataclass
class FinalIndustryReport:
    keyword: str
    generated_at: str
    global_summary: str
    decisions: List[ConflictDecision] = field(default_factory=list)
    raw_sources_count: int = 0