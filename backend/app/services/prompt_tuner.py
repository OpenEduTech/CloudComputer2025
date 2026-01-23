# -*- coding: utf-8 -*-
"""
Prompt Tuner
材料驱动提示优化器：根据输入材料（文本/事实）提炼领域提示、单位、时间短语等，
用于增强提取、验证、冲突检测的提示效果。
"""
import re
from typing import Dict, Any, List, Tuple

UNITS_PATTERNS = [
    r"\%", r"万元|人民币|元|美元|万元人民币|亿|万", r"人|户|家|台|件|公里|米|平方米|亩",
]
TIME_PATTERNS = [
    r"\d{4}年\d{1,2}月\d{1,2}日", r"\d{4}年\d{1,2}月", r"\d{4}年", r"\d{1,2}月\d{1,2}日",
    r"\d{4}-\d{1,2}-\d{1,2}", r"\d{4}-\d{1,2}", r"\d{4}/\d{1,2}/\d{1,2}",
    r"月底|年初|年末|上半年|下半年|季度|Q\d",
]

class PromptTuner:
    def derive_hints_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取关键词、单位、时间短语等提示信息。"""
        text = text or ""
        # 简单关键词（中文/英文词，长度>=2）
        tokens = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z]{2,}", text)
        keywords = list({t for t in tokens if len(t) >= 2})[:20]
        # 单位
        units: List[str] = []
        for pat in UNITS_PATTERNS:
            units += re.findall(pat, text)
        units = list({u for u in units})
        # 时间短语
        times: List[str] = []
        for pat in TIME_PATTERNS:
            times += re.findall(pat, text)
        times = list({t for t in times})
        return {
            "keywords": keywords,
            "units": units,
            "time_phrases": times,
        }

    def build_verification_queries(self, fact: Dict[str, Any]) -> List[str]:
        """用结构字段组合1-2个查询语句，避免过度依赖LLM生成。"""
        subject = (fact.get("subject") or "").strip()
        predicate = (fact.get("predicate") or "").strip()
        obj = (fact.get("object") or "").strip()
        time = (fact.get("time") or "").strip()
        content = (fact.get("content") or "").strip()
        queries: List[str] = []
        base = " ".join([p for p in [subject, predicate, obj, time] if p])
        if base:
            queries.append(base)
        # 次选用原始内容（截断至较短）
        if content:
            queries.append(content[:200])
        return queries[:2]

# 全局实例
prompt_tuner = PromptTuner()
