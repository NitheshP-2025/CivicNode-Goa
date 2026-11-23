"""Field validation, normalisation and comparison helpers."""
from __future__ import annotations

import re
from typing import Optional, Tuple

from rapidfuzz import fuzz

from ..config import load_thresholds

_TITLES = re.compile(r"\b(?:shri|shree|sri|smt|sau|kum|late|mr|mrs|ms|dr)\b\.?", re.I)
_SURVEY_OK = re.compile(r"^\d{1,4}(?:/[0-9A-Z]{1,4})?$")
# Hectare-Are-Square metre, e.g. 1-20-50 = 1 ha + 20 are + 50 sq m.
# ASSUMPTION: confirm that Goa's Form I & XIV prints area this way.
_HAS = re.compile(r"^\s*(\d+)\s*[-–/]\s*(\d{1,2})\s*[-–/]\s*(\d{1,2}(?:\.\d+)?)\s*$")
_WITH_UNIT = re.compile(
    r"(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>hect\w*|ha|acres?|ares?|sq\.?\s*m\w*|sqm|m2|m²)", re.I)
_TO_HA = {"ha": 1.0, "acre": 0.40468564224, "are": 0.01, "sqm": 0.0001}


def _unit_key(unit: str) -> str:
    u = unit.lower().replace(".", "").replace(" ", "")
    if u.startswith("hect") or u == "ha":
        return "ha"
    if u.startswith("acre"):
        return "acre"
    if u.startswith("are"):
        return "are"
    return "sqm"


def parse_area(text) -> Tuple[Optional[float], Optional[str]]:
    """Return (area in hectares, original unit label) or (None, None)."""
    if text is None:
        return None, None
    s = str(text).strip()
    m = _HAS.match(s)
    if m:
        ha = int(m.group(1)) + int(m.group(2)) / 100 + float(m.group(3)) / 10000
        return round(ha, 6), "H-A-S"
    m = _WITH_UNIT.search(s)
    if m:
        num = re.sub(r",(?=\d{3}\b)", "", m.group("num")).replace(",", ".")
        key = _unit_key(m.group("unit"))
        return round(float(num) * _TO_HA[key], 6), key
    return None, None


def normalize_survey(text) -> str:
    s = re.sub(r"\s+", "", str(text).strip().upper())
    return re.sub(r"[-\\]", "/", s)


def to_roman(text: str) -> str:
    """Devanagari to Roman letters so Konkani/Marathi and English names can be compared."""
    if not any("\u0900" <= c <= "\u097F" for c in text):
        return text
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except Exception:
        return text


def normalize_name(text) -> str:
    s = to_roman(str(text)).lower()
    s = _TITLES.sub(" ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_place(text) -> str:
    return normalize_name(text)


def validate_field(name: str, value) -> bool:
    if value is None:
        return False
    if name == "survey":
        return bool(_SURVEY_OK.match(normalize_survey(value)))
    if name == "area_ha":
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False
        return 0 < v < 10000
    text = str(value).strip()
    if name == "owner":
        digits = sum(c.isdigit() for c in text)
        return len(text) >= 3 and digits <= 0.1 * len(text)
    return len(text) >= 2


def values_agree(name: str, a, b) -> bool:
    """Do two readings of the same field mean the same thing?"""
    if a is None or b is None:
        return False
    cfg = load_thresholds()
    if name == "survey":
        return normalize_survey(a) == normalize_survey(b)
    if name == "area_ha":
        try:
            fa, fb = float(a), float(b)
        except (TypeError, ValueError):
            return False
        base = max(abs(fa), abs(fb))
        tol = cfg["extraction"]["agree_area_tolerance_pct"] / 100.0
        return base == 0 or abs(fa - fb) / base <= tol
    if name == "owner":
        score = fuzz.token_sort_ratio(normalize_name(a), normalize_name(b))
        return score >= cfg["matching"]["name_match_score"]
    return normalize_place(a) == normalize_place(b)
