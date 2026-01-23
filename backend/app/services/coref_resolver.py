# -*- coding: utf-8 -*-
"""
Simple coreference resolver heuristics.
- Track last explicit subject within section scope
- Resolve implicit subjects like "本项目", "该公司", "其" to last subject
"""
from typing import Dict, Any, Optional

IMPLICIT_SUBJECT_TOKENS = ["\u672c\u9879\u76ee", "\u8be5\u9879\u76ee", "\u6211\u4eec\u516c\u53f8", "\u8be5\u516c\u53f8", "\u5176", "\u5b83"]


def extract_explicit_subject(fact: Dict[str, Any]) -> Optional[str]:
    # Heuristic: prefer canonical entities, fall back to leading noun phrase from content
    canon_entities = fact.get("canonical", {}).get("entities", [])
    if canon_entities:
        return canon_entities[0]
    content = fact.get("content", "")
    # naive split by key separators to get a leading chunk
    for sep in ["\u662f", "\u4e3a", "\u5728", "\u4e8e", "\u7684"]:
        if sep in content:
            cand = content.split(sep)[0].strip()
            if len(cand) >= 2:
                return cand
    return None


def resolve_subject(fact: Dict[str, Any], last_subject: Optional[str]) -> str:
    content = fact.get("content", "")
    # If content starts with implicit tokens, use last_subject
    for tok in IMPLICIT_SUBJECT_TOKENS:
        if tok in content:
            return last_subject or fact.get("subject") or tok
    # Else try to extract explicit subject
    explicit = extract_explicit_subject(fact)
    return explicit or last_subject or fact.get("subject")
