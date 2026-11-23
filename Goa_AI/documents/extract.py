from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Dict, List, Optional

import cv2
import numpy as np

from ..config import load_thresholds
from ..schemas import ExtractionResult, FieldResult
from .ocr import Word, group_lines, run_ocr
from .preprocess import load_images, prepare_for_ocr
from .quality import check_quality
from .validate import normalize_survey, parse_area, validate_field, values_agree

log = logging.getLogger(__name__)

FIELD_ORDER = ["owner", "survey", "area_ha", "village", "taluka"]

# PLACEHOLDER labels. Replace with the real printed labels once you have
# real Form I & XIV samples. Longest labels are tried first.
LABELS: Dict[str, List[str]] = {
    "survey": ["survey number", "survey no", "sy no", "सर्वे नं", "सर्व्हे नं", "सर्वे क्रमांक"],
    "owner": ["name of owner", "name of occupant", "owner", "occupant", "holder",
              "मालक", "भोगवटादार", "कब्जेदार"],
    "village": ["village", "गाव", "गांव"],
    "taluka": ["taluka", "तालुका"],
    "area_ha": ["area", "क्षेत्रफळ", "क्षेत्र"],
}


def _alts(labels: List[str]) -> str:
    return "|".join(re.escape(l) for l in sorted(labels, key=len, reverse=True))


_LABEL_RE = {
    n: re.compile(r"(?<![A-Za-z])(?:%s)\s*[:\-–.]*\s*(?P<v>\S.*?)\s*$" % _alts(ls), re.I)
    for n, ls in LABELS.items()
}
_OTHER_LABELS = {
    n: re.compile(r"(?<![A-Za-z])(?:%s)" % _alts([l for k, ls in LABELS.items() if k != n for l in ls]), re.I)
    for n in LABELS
}
_AREA_ANY = re.compile(
    r"\d+\s*[-–/]\s*\d{1,2}\s*[-–/]\s*\d{1,2}(?:\.\d+)?"
    r"|\d+(?:[.,]\d+)?\s*(?:hect\w*|ha|acres?|ares?|sq\.?\s*m\w*|sqm|m2|m²)", re.I)


def _line_text(words: List[Word]):
    text, offs = "", []
    for w in words:
        if text:
            text += " "
        start = len(text)
        text += w.text
        offs.append((start, len(text)))
    return text, offs


def _words_in_span(words, offs, start, end):
    return [w for w, (s, e) in zip(words, offs) if s < end and e > start]


def _union_bbox(ws: List[Word]) -> Optional[List[float]]:
    if not ws:
        return None
    x0 = min(w.bbox[0] for w in ws)
    y0 = min(w.bbox[1] for w in ws)
    x1 = max(w.bbox[0] + w.bbox[2] for w in ws)
    y1 = max(w.bbox[1] + w.bbox[3] for w in ws)
    return [round(x0, 4), round(y0, 4), round(x1 - x0, 4), round(y1 - y0, 4)]


def _ocr_candidates(lines: List[List[Word]]) -> Dict[str, dict]:
    default_conf = load_thresholds()["extraction"]["ocr_default_confidence"]
    found: Dict[str, dict] = {}
    for words in lines:
        text, offs = _line_text(words)
        for name in FIELD_ORDER:
            if name in found:
                continue
            m = _LABEL_RE[name].search(text)
            if not m:
                continue
            v_start, v_end = m.start("v"), m.end("v")
            raw = text[v_start:v_end]
            unit = None
            if name == "area_ha":
                am = _AREA_ANY.search(raw)
                if not am:
                    continue
                value, unit = parse_area(am.group(0))
                if value is None:
                    continue
                v_start, v_end = v_start + am.start(), v_start + am.end()
            elif name == "survey":
                sm = re.match(r"[0-9A-Za-z/\\\-]+", raw)
                if not sm:
                    continue
                value = normalize_survey(sm.group(0))
                v_end = v_start + sm.end()
            else:
                cut = _OTHER_LABELS[name].search(raw)
                if cut:
                    raw = raw[:cut.start()]
                    v_end = v_start + cut.start()
                value = raw.strip(" :-–.,")
                if not value:
                    continue
            ws = _words_in_span(words, offs, v_start, v_end)
            conf = sum(w.conf for w in ws) / len(ws) if ws else default_conf
            found[name] = {"value": value, "conf": conf, "unit": unit,
                           "bbox": _union_bbox(ws), "page": ws[0].page if ws else 0}
    return found


LLM_PROMPT = (
    "You are reading a scanned Goa land record (Form I & XIV or similar). "
    "Return ONLY a JSON object with keys: is_land_record (true/false), owner, survey, "
    "village, taluka, area_text (exactly as printed, with its unit). "
    "Use null for anything you cannot read clearly. Do not guess."
)


# Groq model IDs change. Check https://console.groq.com/docs/vision for a current
# vision-capable model and set GROQ_MODEL in your environment to override this default.
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"
MAX_IMAGES = 3          # stay under Groq's per-request image limit
MAX_SIDE_PX = 1600      # downscale big photos so the request stays small and fast


def _downscale(img: np.ndarray) -> np.ndarray:
    scale = MAX_SIDE_PX / max(img.shape[:2])
    if scale >= 1:
        return img
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def _parse_json(text: str) -> Optional[dict]:
    """Pull the JSON object out of a model reply (handles code fences and <think> blocks)."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    text = re.sub(r"```(?:json)?", "", text)
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b <= a:
        return None
    try:
        out = json.loads(text[a:b + 1])
    except json.JSONDecodeError:
        return None
    return out if isinstance(out, dict) else None


def llm_extract(images: List[np.ndarray]) -> Optional[dict]:
    """Vision-model reading via Groq. Returns None when unavailable so OCR still works."""
    if not os.getenv("GROQ_API_KEY"):
        return None
    try:
        from groq import Groq

        client = Groq()   # reads GROQ_API_KEY from the environment
        content = [{"type": "text", "text": LLM_PROMPT}]
        for img in images[:MAX_IMAGES]:
            ok, buf = cv2.imencode(".jpg", _downscale(img), [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                b64 = base64.b64encode(buf.tobytes()).decode()
                content.append({"type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        kwargs = dict(model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
                      messages=[{"role": "user", "content": content}],
                      temperature=0, max_tokens=800)
        try:
            resp = client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
        except Exception:   # some models reject JSON mode with images; retry as plain text
            resp = client.chat.completions.create(**kwargs)
        return _parse_json(resp.choices[0].message.content)
    except Exception as e:  # never let the vision step break the pipeline
        log.warning("llm_extract failed: %s", e)
        return None


def _clean(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _llm_value(name: str, llm: Optional[dict]):
    """Returns (value, unit) from the vision model's answer."""
    if not llm:
        return None, None
    if name == "area_ha":
        return parse_area(llm.get("area_text"))
    v = _clean(llm.get(name))
    if v and name == "survey":
        v = normalize_survey(v)
    return v, None


def _merge(name: str, ocr: Optional[dict], llm_val):
    e = load_thresholds()["extraction"]
    ocr_val = ocr["value"] if ocr else None
    ocr_conf = ocr["conf"] if ocr else 0.0
    if ocr_val is None and llm_val is None:
        return None, 0.0, None
    if ocr_val is not None and llm_val is not None:
        if values_agree(name, ocr_val, llm_val):
            value, conf, src = ocr_val, 0.5 * ocr_conf + 0.5, "ocr+llm"
        else:
            use_ocr = validate_field(name, ocr_val)
            value = ocr_val if use_ocr else llm_val
            conf = min(e["disagree_cap"], ocr_conf if use_ocr else e["disagree_cap"])
            src = "ocr" if use_ocr else "llm"
    elif ocr_val is not None:
        value, conf, src = ocr_val, e["single_source_factor"] * ocr_conf, "ocr"
    else:
        value, conf, src = llm_val, e["llm_only_confidence"], "llm"
    if not validate_field(name, value):
        conf *= e["invalid_factor"]
    return value, round(float(conf), 3), src


def extract_document(data: bytes, filename: str, document_id: str) -> ExtractionResult:
    """Full pipeline for one uploaded document. Raises ValueError for unreadable files."""
    images = load_images(data, filename)
    qualities = [check_quality(img) for img in images]
    worst = next((q for q in qualities if not q.ok), qualities[0])
    notes: List[str] = []

    if not worst.ok:
        # Ask for a better upload instead of guessing from a bad image.
        return ExtractionResult(document_id=document_id, quality=worst, is_land_record=True,
                                fields=[], notes=["extraction_skipped_poor_quality"])

    words: List[Word] = []
    try:
        for i, img in enumerate(images):
            words += run_ocr(prepare_for_ocr(img), page=i)
    except Exception as e:  # Tesseract missing or language pack missing
        log.warning("OCR unavailable: %s", e)
        notes.append("ocr_unavailable")

    ocr = _ocr_candidates(group_lines(words))
    llm = llm_extract(images)
    if llm is None:
        notes.append("llm_unavailable")

    fields: List[FieldResult] = []
    for name in FIELD_ORDER:
        llm_val, llm_unit = _llm_value(name, llm)
        value, conf, src = _merge(name, ocr.get(name), llm_val)
        o = ocr.get(name) or {}
        from_ocr = src in ("ocr", "ocr+llm")
        fields.append(FieldResult(
            name=name, value=value, confidence=conf,
            bbox=o.get("bbox") if from_ocr else None,
            page=o.get("page", 0) if from_ocr else 0,
            unit_original=(o.get("unit") if from_ocr else llm_unit) if name == "area_ha" else None,
            source=src))

    if llm is not None and isinstance(llm.get("is_land_record"), bool):
        is_land = llm["is_land_record"]
    elif not words and llm is None:
        is_land = True   # nothing could run; this is a system gap, not a bad document
        notes.append("no_extraction_backend")
    else:
        is_land = sum(1 for k in ("survey", "owner", "area_ha") if k in ocr) >= 2

    return ExtractionResult(document_id=document_id, quality=worst,
                            is_land_record=is_land, fields=fields, notes=notes)
