"""Pull claim fields out of a speech-to-text transcript (English/Marathi/Konkani).

This is deliberately rule-based: it is predictable, needs no model download
and never invents a value. Whatever it extracts is read back to the farmer for
confirmation, so a miss costs one retry, not a wrong claim.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Dict, Optional

from .lang import DEVANAGARI_DIGITS, MONTH_LOOKUP, NO_WORDS, STRONG_YES

_NL = r"(?<![\wऀ-ॿ])"   # "not preceded by a word character" (Devanagari aware)
_NR = r"(?![\wऀ-ॿ])"    # "not followed by a word character"
_TOKEN = re.compile(r"[\wऀ-ॿ]+|[,.;।]")

STOPWORDS = {
    "and", "survey", "village", "from", "my", "phone", "mobile", "number", "no", "is",
    "the", "flood", "date", "on", "in", "at", "of", "name", "contact",
    "आणि", "आनी", "आहे", "आसा", "आसात", "गाव", "गांव", "गावाचे", "गांवाचें",
    "सर्वे", "सर्व्हे", "मोबाईल", "मोबाइल", "फोन", "क्रमांक", "नंबर", "पुराची",
    "पूर", "तारीख", "माझे", "म्हजें", "म्हजे", "म्हजो", "नाव", "नांव",
}
_NAME_LEAD_SKIP = {"is", "आहे", "आसा", "name", "नाव", "नांव"}
_GREETINGS = {"hello", "hi", "namaste", "नमस्कार", "नमस्ते", "मी", "i", "am", "m"}
_VILLAGE_LEAD_SKIP = {"is", "name", "of", "आहे", "आसा", "नाव", "नांव"}
_VILLAGE_PRECEDERS = {"village", "गावाचे", "गावाचं", "गांवाचें", "गांवाचे", "गावाचा", "गांवाचो"}
_NOT_A_VALUE = STRONG_YES | NO_WORDS | {"correct", "right"}

# ----------------------------------------------------------------------
# normalisation + spoken English numbers
# ----------------------------------------------------------------------
_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
          "six": 6, "seven": 7, "eight": 8, "nine": 9}
_TEENS = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
          "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_NUMBER_WORDS = set(_UNITS) | set(_TEENS) | set(_TENS) | {"hundred"}


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFC", text or "")
    t = t.translate(DEVANAGARI_DIGITS).replace("‌", "").replace("‍", "")
    return re.sub(r"\s+", " ", t).strip()


def _parse_number(tokens, i):
    n, j, total, matched = len(tokens), i, 0, False
    if j + 1 < n and tokens[j] in _UNITS and tokens[j + 1] == "hundred":
        total, j, matched = _UNITS[tokens[j]] * 100, j + 2, True
        if j + 1 < n and tokens[j] == "and" and tokens[j + 1] in _NUMBER_WORDS:
            j += 1
    if j < n and tokens[j] in _TEENS:
        total, j, matched = total + _TEENS[tokens[j]], j + 1, True
    elif j < n and tokens[j] in _TENS:
        total, j, matched = total + _TENS[tokens[j]], j + 1, True
        if j < n and tokens[j] in _UNITS and _UNITS[tokens[j]] != 0:
            total, j = total + _UNITS[tokens[j]], j + 1
    elif j < n and tokens[j] in _UNITS:
        total, j, matched = total + _UNITS[tokens[j]], j + 1, True
    return (total, j) if matched else (None, i)


def convert_english_number_words(text: str) -> str:
    """'survey number forty five slash two' -> 'survey number 45 / 2'."""
    tokens = re.findall(r"[\wऀ-ॿ]+|[^\w\sऀ-ॿ]", text)
    if not any(t.lower() in _NUMBER_WORDS or t.lower() == "slash" for t in tokens):
        return text
    low = [t.lower() for t in tokens]
    out, i = [], 0
    while i < len(tokens):
        if low[i] == "slash":
            out.append("/")
            i += 1
            continue
        val, j = _parse_number(low, i)
        if val is not None:
            out.append(str(val))
            i = j
        else:
            out.append(tokens[i])
            i += 1
    return " ".join(out)


# ----------------------------------------------------------------------
# dates
# ----------------------------------------------------------------------
_MON = "|".join(re.escape(k) for k in sorted(MONTH_LOOKUP, key=len, reverse=True))
_D_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_D_NUM = re.compile(r"(?<!\d)(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})(?!\d)")
_D_DM = re.compile(rf"(?<!\d)(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MON}){_NR}\s*,?\s*(\d{{4}})?(?!\d)", re.I)
_D_MD = re.compile(rf"{_NL}({_MON})\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*(\d{{4}})?(?!\d)", re.I)


def _mk(y, m, d) -> Optional[str]:
    try:
        if not 1990 <= y <= 2100:
            return None
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def parse_date(text: str, assume_year: Optional[int] = None) -> Optional[str]:
    """Return an ISO date (YYYY-MM-DD) or None. Numeric dates are day-first."""
    t = normalize(text)
    for m in _D_ISO.finditer(t):
        r = _mk(int(m[1]), int(m[2]), int(m[3]))
        if r:
            return r
    for m in _D_NUM.finditer(t):
        r = _mk(int(m[3]), int(m[2]), int(m[1]))
        if r:
            return r
    for m in _D_DM.finditer(t):
        year = int(m[3]) if m[3] else assume_year
        if year:
            r = _mk(year, MONTH_LOOKUP[m[2].lower()], int(m[1]))
            if r:
                return r
    for m in _D_MD.finditer(t):
        year = int(m[3]) if m[3] else assume_year
        if year:
            r = _mk(year, MONTH_LOOKUP[m[1].lower()], int(m[2]))
            if r:
                return r
    return None


# ----------------------------------------------------------------------
# free-text helpers
# ----------------------------------------------------------------------
def _take_words(rest: str, lead_skip=frozenset(), max_words: int = 4) -> Optional[str]:
    words = []
    for m in _TOKEN.finditer(rest):
        w = m.group(0)
        if w in ",.;।":
            break
        lw = w.lower()
        if not words and lw in lead_skip:
            continue
        if lw in STOPWORDS or w[0].isdigit():
            break
        words.append(w)
        if len(words) >= max_words:
            break
    return " ".join(words) if words else None


def _take_words_before(before: str, max_words: int = 2) -> Optional[str]:
    words = []
    for m in reversed(list(_TOKEN.finditer(before))):
        w = m.group(0)
        if w in ",.;।" or w.lower() in STOPWORDS or w[0].isdigit():
            break
        words.append(w)
        if len(words) >= max_words:
            break
    return " ".join(reversed(words)) if words else None


# ----------------------------------------------------------------------
# field patterns
# ----------------------------------------------------------------------
_SURVEY_KW = (
    r"(?:survey|sarvey|servey)\s*(?:number|no\.?|num|#)?"
    r"|सर्वे\s*(?:नंबर|नं\.?|क्रमांक|क्र\.?)?"
    r"|सर्व्हे\s*(?:नंबर|नं\.?|क्रमांक|क्र\.?)?"
)
_SURVEY_VALUE = r"(\d{1,4}(?:\s*/\s*\d{1,3}[A-Za-z]?)?)"
_SURVEY_RE = re.compile(rf"{_NL}(?:{_SURVEY_KW})\s*(?:is|आहे|आसा|:|-|=)?\s*{_SURVEY_VALUE}", re.I)
_BARE_SURVEY_RE = re.compile(rf"(?:is\s+)?{_SURVEY_VALUE}\.?", re.I)

_NAME_KW_RE = re.compile(
    rf"{_NL}(?:my\s+name\s+is|name\s+is|my\s+name|name|नाव|नांव|नाम){_NR}", re.I)
_VILLAGE_KW_RE = re.compile(
    rf"{_NL}(?:village\s+name|village|गावाचे\s+नाव|गावाचं\s+नाव|गांवाचें\s+नांव|"
    rf"गांवाचे\s+नांव|गाव|गांव|ग्राम){_NR}", re.I)
_PHONE_KW_RE = re.compile(
    rf"{_NL}(?:phone|mobile|contact|cell|फोन|मोबाईल|मोबाइल|संपर्क)"
    rf"(?:\s*(?:number|no\.?|नंबर|क्रमांक))?[^\d]{{0,15}}((?:\d[\s\-]?){{10,14}})", re.I)
_PHONE_BARE_RE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")


def _survey(t: str) -> Optional[str]:
    m = _SURVEY_RE.search(t)
    if not m:
        return None
    v = re.sub(r"\s+", "", m.group(1))
    return v[:-1] + v[-1].upper() if v[-1].isalpha() else v


def _name(t: str) -> Optional[str]:
    for m in _NAME_KW_RE.finditer(t):
        prev = re.findall(r"[\wऀ-ॿ]+", t[: m.start()])
        if prev and prev[-1].lower() in _VILLAGE_PRECEDERS:
            continue
        words = _take_words(t[m.end():], _NAME_LEAD_SKIP)
        if words:
            return words
    return None


def _village(t: str) -> Optional[str]:
    for m in _VILLAGE_KW_RE.finditer(t):
        after = _take_words(t[m.end():], _VILLAGE_LEAD_SKIP)
        if after:
            return after
        before = _take_words_before(t[: m.start()])
        if before:
            return before
    return None


def _phone(t: str) -> Optional[str]:
    m = _PHONE_KW_RE.search(t)
    if m:
        digits = re.sub(r"\D", "", m.group(1))[:10]
        if len(digits) == 10 and digits[0] in "6789":
            return digits
    m = _PHONE_BARE_RE.search(t)
    return m.group(1) if m else None


def extract_fields(text: str, language: str = "en", assume_year: Optional[int] = None,
                   allow_bare: Optional[str] = None) -> Dict[str, str]:
    """Return {field: value} for whatever could be found in ``text``.

    Keywords for all three languages are matched regardless of ``language``
    because speakers mix languages. ``allow_bare`` names a field the farmer was
    just asked for, so a bare answer such as "Valpoi" can be accepted for it.
    """
    t = convert_english_number_words(normalize(text))
    if not t:
        return {}
    out: Dict[str, str] = {}
    v = _survey(t)
    if v:
        out["survey_no"] = v
    v = _name(t)
    if v:
        out["name"] = v
    v = _village(t)
    if v:
        out["village"] = v
    v = parse_date(t, assume_year)
    if v:
        out["incident_date"] = v
    v = _phone(t)
    if v:
        out["phone"] = v

    if allow_bare and allow_bare not in out:
        if allow_bare in ("name", "village"):
            words = _take_words(t, _GREETINGS)
            if words and words.lower() not in _NOT_A_VALUE:
                out[allow_bare] = words
        elif allow_bare == "survey_no":
            m = _BARE_SURVEY_RE.fullmatch(t)
            if m:
                out["survey_no"] = re.sub(r"\s+", "", m.group(1))
    return out


def missing_fields(fields: Dict[str, str], required) -> list:
    return [f for f in required if not fields.get(f)]
