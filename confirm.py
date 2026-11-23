"""Repeat-back confirmation text and yes/no understanding, in three languages."""
from __future__ import annotations

import re
from datetime import date
from typing import Dict, Iterable, Optional

from .lang import (DISPLAY_MONTHS, FIELD_LABELS, FIELD_ORDER, NO_WORDS,
                   STRONG_YES, SUPPORTED, TEXT, WEAK_YES)

_WORD = re.compile(r"[\wऀ-ॿ]+")


def _check_lang(language: str) -> str:
    if language not in SUPPORTED:
        raise ValueError(f"unsupported language {language!r}; use one of {SUPPORTED}")
    return language


def format_date(iso: str, language: str) -> str:
    """'2021-07-22' -> '22 July 2021' (month name in the chosen language)."""
    _check_lang(language)
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{d.day} {DISPLAY_MONTHS[language][d.month - 1]} {d.year}"


def render_repeat_back(fields: Dict[str, str], language: str) -> str:
    """Sentence read back to the farmer: 'I heard: name ..., survey number ...'."""
    _check_lang(language)
    labels = FIELD_LABELS[language]
    parts = []
    for key in FIELD_ORDER:
        value = fields.get(key)
        if not value:
            continue
        if key == "incident_date":
            value = format_date(value, language)
        parts.append(f"{labels[key]} {value}")
    return TEXT["heard"][language].format(parts=", ".join(parts))


def render_ask(missing: Iterable[str], language: str) -> str:
    """'Please tell me your name, survey number.' for the fields still needed."""
    _check_lang(language)
    labels = FIELD_LABELS[language]
    items = ", ".join(labels[f] for f in missing)
    return TEXT["ask"][language].format(items=items)


def parse_yes_no(text: str) -> Optional[bool]:
    """True = yes, False = no, None = unclear."""
    words = {w.lower() for w in _WORD.findall(text or "")}
    has_no = bool(words & NO_WORDS)
    has_strong = bool(words & STRONG_YES)
    has_weak = bool(words & WEAK_YES)
    if has_no and has_strong:
        return None
    if has_no:
        return False
    if has_strong or has_weak:
        return True
    return None
