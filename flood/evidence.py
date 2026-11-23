"""Evidence image for the officer screen: satellite water mask with the plot outlined."""
from __future__ import annotations

import io
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .layer import FloodLayer
from .query import normalize_plot, to_date

LAND = (238, 236, 228)
PERMANENT = (70, 90, 120)
FLOODED = (30, 120, 255)
NO_DATA = (190, 190, 190)
PLOT = (220, 30, 30)


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:       # very old Pillow
        return ImageFont.load_default()


def render_evidence_png(layer: FloodLayer, plot: Any, on_date: Union[str, date, datetime],
                        out_path: Optional[Union[str, Path]] = None, pad_px: int = 60,
                        max_side: int = 900) -> bytes:
    qdate = to_date(on_date)
    _pid, ring = normalize_plot(plot)
    near = layer.nearest_observation(qdate)
    if near is None:
        raise ValueError("layer has no observations")
    t, gap = near

    pix = [layer.lonlat_to_ij(lon, lat) for lon, lat in ring]
    i_lo, i_hi = min(p[0] for p in pix), max(p[0] for p in pix)
    j_lo, j_hi = min(p[1] for p in pix), max(p[1] for p in pix)
    i0, i1 = max(0, i_lo - pad_px), min(layer.height, i_hi + pad_px + 1)
    j0, j1 = max(0, j_lo - pad_px), min(layer.width, j_hi + pad_px + 1)
    if i0 >= i1 or j0 >= j1:
        raise ValueError("plot is outside the area covered by the flood layer")

    water = layer.water[t, i0:i1, j0:j1]
    valid = layer.valid[t, i0:i1, j0:j1]
    perm = layer.permanent[i0:i1, j0:j1]
    rgb = np.empty(water.shape + (3,), dtype=np.uint8)
    rgb[:] = LAND
    rgb[~valid] = NO_DATA
    rgb[water & valid & ~perm] = FLOODED
    rgb[perm] = PERMANENT

    h, w = water.shape
    scale = max(1, min(max_side // max(h, w), 12))
    img = Image.fromarray(rgb, "RGB").resize((w * scale, h * scale), Image.NEAREST)
    draw = ImageDraw.Draw(img)
    pts = [((j - j0 + 0.5) * scale, (i - i0 + 0.5) * scale) for i, j in pix]
    draw.line(pts + [pts[0]], fill=PLOT, width=max(2, scale // 2))

    # caption bar + legend
    font = _font(14)
    bar_h = 64
    canvas = Image.new("RGB", (max(img.width, 420), img.height + bar_h), (255, 255, 255))
    canvas.paste(img, (0, 0))
    d = ImageDraw.Draw(canvas)
    obs = layer.dates[t].isoformat()
    d.text((8, img.height + 6), f"Satellite pass: {obs}   Claimed date: {qdate.isoformat()}   Gap: {gap} day(s)", fill=(0, 0, 0), font=font)
    x = 8
    for colour, label in ((FLOODED, "flooded (normally dry)"), (PERMANENT, "normally wet"),
                          (NO_DATA, "no data"), (PLOT, "plot")):
        d.rectangle((x, img.height + 36, x + 14, img.height + 50), fill=colour)
        d.text((x + 20, img.height + 35), label, fill=(0, 0, 0), font=font)
        x += 24 + int(d.textlength(label, font=font)) + 14
    if layer.meta.get("is_synthetic"):
        d.rectangle((0, 0, canvas.width, 24), fill=(255, 215, 0))
        d.text((8, 4), "SYNTHETIC DEMO DATA - NOT REAL SATELLITE EVIDENCE", fill=(0, 0, 0), font=font)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    data = buf.getvalue()
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(data)
    return data
