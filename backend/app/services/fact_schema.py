# -*- coding: utf-8 -*-
"""
Fact Schema helpers (dict-based)
Provides utilities to ensure consistent keys and defaults.
"""
from typing import Dict, Any

DEFAULT_FACT_KEYS = {
    "subject": None,
    "predicate": None,
    "object": None,
    "value": None,
    "modifiers": {},
    "time": None,
    "polarity": "affirmative",  # or "negative"
    "type": "未知",
    "verifiable_type": "public",
    "scope_path": None,
    "span": None,
    "confidence": 0.0,
    "canonical": {},
    "aliases": [],
    "source_hints": [],
}


def ensure_schema(fact: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure fact dict contains standard keys with defaults."""
    for k, v in DEFAULT_FACT_KEYS.items():
        fact.setdefault(k, v)
    return fact


def enrich_location(fact: Dict[str, Any], section_title: str, section_index: int) -> Dict[str, Any]:
    loc = fact.get("location", {})
    loc.update({
        "section_title": section_title,
        "section_index": section_index
    })
    fact["location"] = loc
    return fact
