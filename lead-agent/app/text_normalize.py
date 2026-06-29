"""Normalize owner messages for lead search (Latin + Devanagari)."""

from __future__ import annotations

import re


def contains_devanagari(text: str) -> bool:
    return bool(re.search(r"[\u0900-\u097F]", text))


def romanize_query(text: str) -> str:
    """Devanagari → Latin (ITRANS) for name matching."""
    if not contains_devanagari(text):
        return text
    try:
        from indic_transliteration.sanscript import DEVANAGARI, ITRANS, transliterate

        return transliterate(text, DEVANAGARI, ITRANS)
    except Exception:
        return text


def latin_tokens(text: str) -> list[str]:
    roman = romanize_query(text)
    return [t.lower() for t in re.findall(r"[A-Za-z]{2,}", roman)]


def search_query_variants(query_text: str) -> list[str]:
    """Distinct query strings to try against the database."""
    raw = query_text.strip()
    if not raw:
        return []

    variants: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        cleaned = " ".join(value.split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            variants.append(cleaned)

    add(raw)
    roman = romanize_query(raw)
    add(roman)
    tokens = latin_tokens(raw)
    if tokens:
        add(" ".join(tokens))
    return variants
