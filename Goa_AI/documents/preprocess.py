from __future__ import annotations

from typing import List

import cv2
import numpy as np


def load_images(data: bytes, filename: str = "") -> List[np.ndarray]:
    """Return one BGR image per page. Raises ValueError for unreadable files."""
    if filename.lower().endswith(".pdf") or data[:4] == b"%PDF":
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ValueError("PDF support needs the 'pymupdf' package") from e
        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as e:
            raise ValueError("Could not open the PDF") from e
        pages = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            else:
                arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            pages.append(arr)
        if not pages:
            raise ValueError("The PDF has no pages")
        return pages

    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not read the image file")
    return [img]


def estimate_skew(gray: np.ndarray, max_angle: float = 10.0, step: float = 0.5) -> float:
    """Projection-profile search for the rotation that makes text rows sharpest."""
    small = cv2.resize(gray, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    binary = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    h, w = binary.shape
    best_angle, best_score = 0.0, -1.0
    for angle in np.arange(-max_angle, max_angle + step, step):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), float(angle), 1.0)
        rot = cv2.warpAffine(binary, m, (w, h), flags=cv2.INTER_NEAREST)
        score = float(np.var(rot.sum(axis=1)))
        if score > best_score:
            best_angle, best_score = float(angle), score
    return best_angle


def prepare_for_ocr(image: np.ndarray, deskew: bool = False) -> np.ndarray:
    """Grayscale + contrast boost. Optionally straighten (changes geometry)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    if deskew:
        angle = estimate_skew(gray)
        if abs(angle) >= 0.5:
            h, w = gray.shape
            m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            gray = cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)
