"from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np


@dataclass
class Word:
    text: str
    conf: float                                  # 0-1
    bbox: Tuple[float, float, float, float]      # x, y, w, h as 0-1 fractions
    page: int
    line_key: Tuple[int, int, int, int]          # page, block, paragraph, line


def run_ocr(gray: np.ndarray, page: int = 0, lang: str | None = None) -> List[Word]:
    import pytesseract  # lazy import so the rest of the module works without it

    lang = lang or os.getenv("OCR_LANGS", "eng+hin+mar")
    data = pytesseract.image_to_data(gray, lang=lang, output_type=pytesseract.Output.DICT)
    h, w = gray.shape[:2]
    words: List[Word] = []
    for i, raw in enumerate(data["text"]):
        text = (raw or "").strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue
        words.append(Word(
            text=text,
            conf=conf / 100.0,
            bbox=(data["left"][i] / w, data["top"][i] / h,
                  data["width"][i] / w, data["height"][i] / h),
            page=page,
            line_key=(page, data["block_num"][i], data["par_num"][i], data["line_num"][i]),
        ))
    return words


def group_lines(words: List[Word]) -> List[List[Word]]:
    """Words grouped into reading-order lines, left to right inside each line."""
    lines: Dict[Tuple[int, int, int, int], List[Word]] = {}
    for w in words:
        lines.setdefault(w.line_key, []).append(w)
    return [sorted(v, key=lambda w: w.bbox[0]) for v in lines.values()]
