from __future__ import annotations
from typing import Dict, List, Any

from scraper_layer import ScraperAgent
from storage_layer import StorageClient
from incremental_analysis import incremental_compare, generate_global_summary
from conflict_resolution import resolve_conflicts
from models import ChangeItem, ConflictDecision, FinalIndustryReport, now_ts
from config import MAX_DECISIONS, MAX_EVIDENCE_PER_DECISION, INCLUDE_DEBUG_FIELDS

def run_pipeline(keyword: str, print_steps: bool = False) -> Dict[str, Any]:
    """主流程编排：采集 -> 增量对比 -> 冲突仲裁 -> 生成全局总结 -> 存储"""
    scraper = ScraperAgent()
    storage = StorageClient()

    # 1. 采集最新资讯
    if print_steps:
        print("--- 步骤 1: 正在采集最新资讯 ---")
    new_items = scraper.fetch(keyword=keyword)
    
    # 2. 加载该行业的旧快照（按 keyword 隔离）
    if print_steps:
        print("--- 步骤 2: 正在加载历史快照 ---")
    old_snapshot = storage.load_latest_snapshot(keyword)

    # 3. 成员 B 的核心逻辑：增量对比
    if print_steps:
        print("--- 步骤 3: 正在进行语义增量对比 ---")
    changes: List[ChangeItem] = incremental_compare(old_snapshot, new_items)
    
    # 4. 成员 B 的核心逻辑：冲突仲裁
    if print_steps:
        print("--- 步骤 4: 正在进行冲突仲裁（官方 > 媒体 > 传闻） ---")
    conflicts: List[ConflictDecision] = resolve_conflicts(changes)

    # 5. 新增：基于所有决策生成全局总评价
    if print_steps:
        print("--- 步骤 5: 正在生成全局总决策 ---\n")
    global_report = generate_global_summary(keyword, conflicts)

    # 本次运行的统一时间戳：用于快照与最终报告文件名对齐
    run_ts = now_ts()

    # 6. 存储当前采集的内容作为未来的“旧快照”
    storage.save_snapshot(keyword=keyword, items=new_items, collected_at=run_ts)

    # 7. 存储最终加工报告，供成员 C 展示
    final_report = FinalIndustryReport(
        keyword=keyword,
        generated_at=run_ts,
        global_summary=global_report,
        decisions=conflicts,
        raw_sources_count=len(new_items),
    )
    final_report_path = storage.save_final_report(final_report)

    # 返回给成员 C 进行展示的完整数据包
    decisions_payload = [
        {
            "field": d.field,
            "old_value": getattr(d, "old_value", "") or "",
            "value": d.final_value,
            "status": getattr(d, "status", "") or "",
            "arbitration": {
                "chosen_source": getattr(d.chosen_source, "value", d.chosen_source),
                "pending_sources": [getattr(s, "value", s) for s in (d.pending_sources or [])],
                "conflicting_values": list(getattr(d, "conflicting_values", []) or []),
            },
            "reason": d.reason,
            **({
                "evidence": [
                    {
                        "title": e.title,
                        "url": e.url,
                        "source": getattr(e.source, "value", e.source),
                        "published_at": e.published_at,
                        "quote": getattr(e, "quote", "") or "",
                        "key_numbers": list(getattr(e, "key_numbers", []) or []),
                        "snippet": getattr(e, "snippet", "") or "",
                    }
                    for e in (getattr(d, "evidence", None) or [])[:MAX_EVIDENCE_PER_DECISION]
                ]
            } if INCLUDE_DEBUG_FIELDS else {}),
            **({"confidence": float(getattr(d, "confidence", 0.0) or 0.0)} if INCLUDE_DEBUG_FIELDS else {}),
        }
        for d in conflicts[:MAX_DECISIONS]
    ]

    # sources 清单（title+url），用于 main 最后打印
    seen = set()
    sources: List[Dict[str, str]] = []
    for it in new_items:
        title = (it.title or "").strip()
        url = (it.url or "").strip() if it.url else ""
        key = url or title
        if not key or key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "title": title,
                "url": url,
                "source": getattr(it.source, "value", it.source) if getattr(it, "source", None) is not None else "",
                "published_at": getattr(it, "published_at", None),
            }
        )
    return {
        "keyword": keyword,
        "generated_at": run_ts,
        "global_summary": global_report, # 全局总决策
        "decisions": decisions_payload,  # 各指标详细决策（JSON-safe）
        "raw_sources_count": len(new_items),
        "raw_changes_count": len(changes),
        "final_report_path": final_report_path,
        "sources": sources,
    }