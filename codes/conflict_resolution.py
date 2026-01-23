from __future__ import annotations
from typing import Dict, List
from models import ChangeItem, ConflictDecision, SOURCE_WEIGHTS, SourceType

def resolve_conflicts(changes: List[ChangeItem]) -> List[ConflictDecision]:
    """冲突仲裁逻辑：按权重选择结论，并将 AI 洞察包装为通俗建议"""
    if not changes:
        return []

    # 1. 按指标字段进行分组
    grouped: Dict[str, List[ChangeItem]] = {}
    for c in changes:
        grouped.setdefault(c.field, []).append(c)

    decisions: List[ConflictDecision] = []
    
    # 2. 针对每个指标进行仲裁
    for field, items in grouped.items():
        # 按预设的来源权重排序（官方 > 媒体 > 传闻）
        items_sorted = sorted(
            items,
            key=lambda x: SOURCE_WEIGHTS.get(x.source, 0.0),
            reverse=True,
        )
        
        # 选择权重最高的条目作为最终结论
        chosen = items_sorted[0]
        
        # 记录被舍弃的低权重来源，供成员 C 进行“待核实”展示
        pending = [i.source for i in items_sorted[1:]]

        # 收集冲突候选值（去重），用于在最终报告中体现“仲裁发生过”
        candidates: List[str] = []
        for it in items_sorted[1:]:
            v = (it.new or "").strip()
            if v and v != (chosen.new or "").strip() and v not in candidates:
                candidates.append(v)
        
        decisions.append(
            ConflictDecision(
                field=field,
                final_value=chosen.new,
                chosen_source=chosen.source,
                pending_sources=pending,
                # 核心改进：理由不再是代码逻辑，而是 AI 生成的行业洞察
                reason=chosen.insight,
                evidence=getattr(chosen, "evidence", []) or [],
                old_value=getattr(chosen, "old", "") or "",
                status=getattr(chosen, "status", "") or "",
                confidence=float(getattr(chosen, "confidence", 0.0) or 0.0),
                conflicting_values=candidates,
            )
        )
        
    return decisions