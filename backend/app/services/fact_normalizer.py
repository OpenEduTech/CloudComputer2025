# -*- coding: utf-8 -*-
"""
Fact normalizer
- Normalize dates, numbers, currency
- Canonicalize entities via simple alias mapping
"""
import re
from typing import Dict, Any

ALIASES = {
    "\u8c37\u6b4c": "Google",            # 谷歌
    "\u6bd4\u5c14\u00b7\u76d6\u8328": "Bill Gates",  # 比尔·盖茨
    "\u57c3\u9f99\u00b7\u9a6c\u65af\u514b": "Elon Musk",  # 埃隆·马斯克
    "\u5409\u591a\u00b7\u8303\u7f57\u82cf\u59c6": "Guido van Rossum",  # 吉多·范罗苏姆
    "Python\u8bed\u8a00": "Python",
    "SpaceX": "SpaceX",
}

DATE_PATTERNS = [
    (re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"), lambda y,m,d: f"{int(y):04d}-{int(m):02d}-{int(d):02d}"),
    (re.compile(r"(\d{4})年(\d{1,2})月"), lambda y,m: f"{int(y):04d}-{int(m):02d}"),
    (re.compile(r"(\d{4})年"), lambda y: f"{int(y):04d}"),
]

CURRENCY_PAT = re.compile(r"([\d,]+(?:\.\d+)?)\s*(万)?\s*美元")


def normalize_text_date(text: str) -> str:
    for pat, fmt in DATE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return fmt(*m.groups())
            except Exception:
                continue
    return None


def normalize_currency(text: str) -> Dict[str, Any]:
    m = CURRENCY_PAT.search(text)
    if not m:
        return {}
    num_str, wan = m.groups()
    val = float(num_str.replace(',', ''))
    if wan:
        val *= 10000
    return {"currency": "USD", "amount": val}


def canonicalize_entities(text: str) -> Dict[str, Any]:
    canon = {}
    for k, v in ALIASES.items():
        if k in text:
            canon.setdefault("entities", []).append(v)
    return canon


def normalize_fact(fact: Dict[str, Any]) -> Dict[str, Any]:
    content = fact.get("content", "")
    original = fact.get("original_text", "")
    # time
    time_norm = normalize_text_date(content) or normalize_text_date(original)
    if time_norm:
        fact["time"] = time_norm
    # currency
    money = normalize_currency(content) or normalize_currency(original)
    if money:
        fact["value"] = money
    # canonical entities
    canon = canonicalize_entities(content + " " + original)
    if canon:
        fact.setdefault("canonical", {}).update(canon)
    return fact
