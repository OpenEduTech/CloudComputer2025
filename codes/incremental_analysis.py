import os
import json
import re
from typing import List, Optional
from langchain_openai import ChatOpenAI
from models import ChangeItem, NewsItem, ReportSnapshot, SourceType, ConflictDecision, SOURCE_WEIGHTS, EvidenceItem
from config import (
    SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, 
    LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE, LLM_MAX_RETRIES,
    REPORT_MODE
)

# API 密钥配置
api_key = os.getenv("SILICONFLOW_API_KEY", "sk-zieigdeeconidojrwencrdvsejqfxaoqvbxeqbsrxmqinlna")

llm = ChatOpenAI(
    api_key=api_key,
    base_url=LLM_BASE_URL,
    model=LLM_MODEL,
    max_retries=LLM_MAX_RETRIES,
    temperature=LLM_TEMPERATURE
)


def _clamp(value: float, low: float = 0.2, high: float = 0.95) -> float:
    return max(low, min(high, value))


def _compute_dynamic_confidence(
    change: dict,
    default_source: SourceType,
    new_items: List[NewsItem],
) -> float:
    """根据来源权重、来源丰富度及 LLM 反馈动态计算置信度。

    优先使用 LLM 返回的 confidence（若有），并与来源信息融合。
    """
    llm_conf_raw = change.get("confidence")
    llm_conf = None
    try:
        if llm_conf_raw is not None:
            llm_conf = float(llm_conf_raw)
    except (TypeError, ValueError):
        llm_conf = None

    # 来源权重
    source_weight = float(SOURCE_WEIGHTS.get(default_source, 0.5))

    # 来源丰富度：采集条数、来源多样性、证据完备度（url/时间）
    total = max(len(new_items), 1)
    count_score = min(1.0, total / 3)

    distinct_sources = len({i.source for i in new_items if i.source is not None})
    source_div_score = min(1.0, distinct_sources / 3)

    evidence_hits = 0
    for item in new_items:
        if item.url:
            evidence_hits += 1
        if item.published_at:
            evidence_hits += 1
    evidence_score = evidence_hits / (2 * total)

    computed = (
        0.45 * source_weight
        + 0.30 * source_div_score
        + 0.15 * count_score
        + 0.10 * evidence_score
    )

    if llm_conf is not None:
        return _clamp(0.6 * llm_conf + 0.4 * computed)
    return _clamp(computed)

def robust_json_parse(text: str) -> list:
    """JSON 强力提取与修复函数"""
    try:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```json\s*|```$', '', text, flags=re.MULTILINE)
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if match:
            try:
                clean_json = re.sub(r',\s*\]', ']', match.group())
                return json.loads(clean_json)
            except: pass
    return []

def incremental_compare(old_snapshot: Optional[ReportSnapshot], new_items: List[NewsItem]) -> List[ChangeItem]:
    """对比新旧数据并生成带洞察的变动项"""
    if not new_items:
        return []

    old_text = "尚未记录历史指标。"
    if old_snapshot and old_snapshot.items:
        old_text = "\n".join([f"- {i.title}: {i.content}" for i in old_snapshot.items])
    
    new_text = "\n".join([f"[{i.source.value}] {i.title}: {i.content}" for i in new_items])

    try:
        response = llm.invoke([
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT_TEMPLATE.format(old_text=old_text, new_text=new_text))
        ])
        
        raw_changes = robust_json_parse(response.content)
        changes: List[ChangeItem] = []

        def _pick_evidence(
            field_name: str,
            new_value: str,
            k: int = 3,
        ) -> tuple[List[EvidenceItem], SourceType, List[NewsItem]]:
            field_key = (field_name or "").strip()
            value_key = (new_value or "").strip()

            def extract_numbers(text: str, max_n: int = 4) -> List[str]:
                t = (text or "").strip()
                if not t:
                    return []

                # 1) 数值范围：10-20、10~20
                range_pat = re.compile(r"\b\d+(?:\.\d+)?\s*(?:-|~|—|–)\s*\d+(?:\.\d+)?\s*(?:%|nm|纳米|亿|万|元|美元|亿元|万元|万亿元)?\b")
                # 2) 单值+单位（只要“更像指标”的数字：带单位 / 两位及以上 / 小数）
                num_pat = re.compile(
                    r"\b\d+(?:\.\d+)?\s*(?:%|nm|纳米|亿元|万亿元|万元|亿|万|元|美元|GWh|GW|MHz|GHz|TB|GB|MB|倍|万人|万台|家|项|篇|次|美元/年|元/年)?\b"
                )

                candidates: List[str] = []
                candidates.extend([m.group(0).strip() for m in range_pat.finditer(t)])
                candidates.extend([m.group(0).strip() for m in num_pat.finditer(t)])

                # 清洗：去掉明显的页码/孤立年份/版权/编号等
                cleaned: List[str] = []
                for c in candidates:
                    if "/" in c:  # 避免 1 / 35 之类
                        continue
                    raw = c.strip()
                    if "©" in t or "版权所有" in t:
                        # 很多 PDF 抬头会出现 ©2025 之类，优先跳过这类噪声
                        pass

                    # 过滤纯年份（1900-2100），除非带单位
                    only_digits = re.fullmatch(r"\d{4}", raw)
                    if only_digits:
                        y = int(raw)
                        if 1900 <= y <= 2100:
                            continue

                    # 过滤无单位的单个数字/小整数（常见为编号、章节、组别）
                    # 允许两位及以上，或带小数，或带单位
                    has_unit = bool(re.search(r"%|nm|纳米|亿元|万亿元|万元|亿|万|元|美元|GWh|GW|MHz|GHz|TB|GB|MB|倍|万人|万台|家|项|篇|次|/年", raw))
                    if not has_unit:
                        if re.fullmatch(r"\d+", raw):
                            try:
                                n = int(raw)
                            except Exception:
                                n = 0
                            if n < 10:
                                continue
                        if re.fullmatch(r"\d+\.\d+", raw) is None and len(re.sub(r"\D", "", raw)) < 2:
                            continue

                    # 过滤明显的版权年份组合（如 ©2025）附近的小数字
                    if "©" in t:
                        # 若 raw 出现在 © 后很近的位置，且为 4 位年份，前面已过滤；这里再过滤一些残留
                        if re.fullmatch(r"\d{1,2}", raw):
                            continue

                    if raw and raw not in cleaned:
                        cleaned.append(raw)
                    if len(cleaned) >= max_n:
                        break
                return cleaned

            def build_quote(text: str, keys: List[str], max_len: int = 110) -> str:
                t = (text or "").strip().replace("\n", " ")
                if not t:
                    return ""

                # 优先：截取包含“关键数字”的句子片段
                if keys:
                    for key in keys:
                        idx = t.find(key)
                        if idx == -1:
                            continue
                        start = max(0, idx - 35)
                        end = min(len(t), idx + 35 + len(key))
                        frag = t[start:end].strip()
                        # 避免抬头类噪声（部门/团队/版权）
                        if any(bad in frag for bad in ["部门", "项目团队", "©", "版权所有"]):
                            continue
                        return frag[:max_len]
                # 否则按关键词截取
                for kw in (field_key, value_key):
                    if kw and kw in t:
                        idx = t.find(kw)
                        start = max(0, idx - 25)
                        end = min(len(t), idx + 60)
                        return t[start:end].strip()[:max_len]
                return t[:max_len]

            def score_item(item: NewsItem) -> int:
                text = f"{item.title} {item.content}".lower()
                score = 0
                if field_key and field_key.lower() in text:
                    score += 3
                if value_key and value_key.lower() in text:
                    score += 2
                if item.url:
                    score += 1
                if item.published_at:
                    score += 1
                return score

            ranked = sorted(new_items, key=score_item, reverse=True)
            picked = ranked[:k]
            primary_source = picked[0].source if picked else new_items[0].source
            evidences: List[EvidenceItem] = []
            for it in picked:
                nums = extract_numbers(it.content)
                quote = build_quote(it.content, nums)
                evidences.append(
                    EvidenceItem(
                        title=it.title,
                        url=it.url,
                        source=it.source,
                        published_at=it.published_at,
                        quote=quote,
                        key_numbers=nums,
                        snippet=quote,
                    )
                )
            return evidences, primary_source, picked
        for c in raw_changes:
            field_name = str(c.get("field", "未知指标"))
            new_value = str(c.get("new", "N/A"))
            evidences, primary_source, picked_items = _pick_evidence(field_name, new_value)
            confidence = _compute_dynamic_confidence(c, primary_source, picked_items or new_items)
            changes.append(ChangeItem(
                field=field_name,
                old=str(c.get("old", "N/A")),
                new=new_value,
                status=str(c.get("status", "changed")),
                insight=str(c.get("insight", "指标发生变动，请关注。")),
                source=primary_source,
                evidence=evidences,
                confidence=confidence,
            ))
        return changes
    except Exception as e:
        print(f"AI 增量分析失败: {e}")
        return []

def generate_global_summary(keyword: str, decisions: List[ConflictDecision]) -> str:
    """基于所有仲裁后的决策，生成全局通俗综述"""
    if not decisions:
        return f"针对 {keyword} 行业，本次巡检未发现显著的指标变动。"

    # 汇总上下文供 AI 总结
    def _fmt_sources(d: ConflictDecision) -> str:
        chosen = getattr(d.chosen_source, "value", d.chosen_source)
        pending = [getattr(s, "value", s) for s in (d.pending_sources or [])]
        if pending:
            return f"采纳来源={chosen}，待核实来源={','.join(pending)}"
        return f"采纳来源={chosen}"

    def _fmt_change(d: ConflictDecision) -> str:
        old_v = (getattr(d, "old_value", "") or "").strip()
        new_v = (d.final_value or "").strip()
        status = (getattr(d, "status", "") or "").strip()
        conf = float(getattr(d, "confidence", 0.0) or 0.0)
        conflict_vals = getattr(d, "conflicting_values", None) or []

        parts: List[str] = []
        if old_v:
            parts.append(f"{old_v} -> {new_v}")
        else:
            parts.append(f"变为 {new_v}")
        if status:
            parts.append(f"状态={status}")
        if conf:
            parts.append(f"置信度={conf:.2f}")
        if conflict_vals:
            parts.append(f"其他候选={';'.join(conflict_vals[:3])}")
        return "，".join(parts)

    summary_context = "\n".join(
        [
            f"- {d.field}: {_fmt_change(d)}；{_fmt_sources(d)}。分析: {d.reason}"
            for d in decisions
        ]
    )

    prompt = f"""你是一个首席行业分析师。请针对以下 {keyword} 行业的变动写一段 100 字以内的全局总结。
    要求：通俗易懂，点出行业整体趋势（利好/利空/震荡），直击要害。
    
    【变动清单】：
    {summary_context}"""
    
    def arbitration_digest(max_items: int = 8) -> str:
        lines: List[str] = []
        conflict_count = 0
        pending_count = 0
        for d in decisions:
            conflicts = list(getattr(d, "conflicting_values", []) or [])
            pending = list(getattr(d, "pending_sources", []) or [])
            if conflicts:
                conflict_count += 1
            if pending:
                pending_count += 1

        if REPORT_MODE == "compact":
            # 精简模式：只给总览，不展开逐条细节
            if conflict_count == 0 and pending_count == 0:
                return "仲裁：未发现明显多源冲突（官方>媒体>传闻优先级规则已启用）。"
            return f"仲裁：冲突项={conflict_count}，待核实项={pending_count}（官方>媒体>传闻优先级规则已启用）。"

        lines.append(f"仲裁项数={len(decisions)}，存在冲突项={conflict_count}，待核实项={pending_count}")

        shown = 0
        for d in decisions:
            if shown >= max_items:
                break
            conflicts = list(getattr(d, "conflicting_values", []) or [])
            pending = list(getattr(d, "pending_sources", []) or [])
            if not conflicts and not pending:
                continue

            chosen = getattr(getattr(d, "chosen_source", None), "value", getattr(d, "chosen_source", ""))
            old_v = (getattr(d, "old_value", "") or "").strip()
            new_v = (getattr(d, "final_value", "") or "").strip()
            conf = float(getattr(d, "confidence", 0.0) or 0.0)
            msg = f"- {d.field}: {old_v + ' -> ' if old_v else ''}{new_v}（采纳={chosen}，置信度={conf:.2f}）"
            if conflicts:
                msg += f"；候选={';'.join(conflicts[:3])}"
            if pending:
                pend = [getattr(s, "value", s) for s in pending]
                msg += f"；待核实来源={','.join(pend)}"
            lines.append(msg)
            shown += 1

        if shown == 0:
            return "仲裁摘要：本次变动项未出现明显多源冲突。"
        return "仲裁摘要：\n" + "\n".join(lines)

    try:
        response = llm.invoke([("user", prompt)])
        base = (response.content or "").strip()
    except Exception:
        base = "行业发生多项变动，整体处于调整期，建议持续关注核心指标。"

    return base + "\n\n" + arbitration_digest()