"""Quality gate: catch blurry, dark or tiny images before wasting time on OCR."""
from __future__ import annotations

import cv2
import numpy as np

from ..config import load_thresholds
from ..schemas import QualityReport

MESSAGES = {
    "LOW_RESOLUTION": "The image is too small. Please upload a larger, clearer photo or scan.",
    "BLURRY": "The photo is blurry. Please retake it holding the phone steady.",
    "DARK": "The photo is too dark. Please retake it in better light.",
    "OVEREXPOSED": "The photo is too bright or has glare. Please retake it away from direct light.",
}


def check_quality(image: np.ndarray) -> QualityReport:
    cfg = load_thresholds()["quality"]
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())

    code = None
    if w < cfg["min_width"] or h < cfg["min_height"]:
        code = "LOW_RESOLUTION"
    elif blur < cfg["min_blur_score"]:
        code = "BLURRY"
    elif brightness < cfg["min_brightness"]:
        code = "DARK"
    elif brightness > cfg["max_brightness"]:
        code = "OVEREXPOSED"

    return QualityReport(
        ok=code is None,
        blur_score=round(blur, 2),
        width=int(w),
        height=int(h),
        brightness=round(brightness, 2),
        code=code,
        message=MESSAGES.get(code) if code else None,
    )
