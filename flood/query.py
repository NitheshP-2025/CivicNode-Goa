"""Answer: "was this plot flooded on this date, and how confident are we?"

Rules (all thresholds in config.py):
* land that is normally wet (rivers, lakes) is ignored - it can never be flood damage;
* the satellite pass closest to the claimed date is used, if within MAX_DAYS_GAP days;
* the verdict comes from the share of the plot's normally-dry area that is under water;
* anything we cannot judge is INCONCLUSIVE (the pipeline turns that into an Amber case).

``confidence`` is a transparent heuristic score in 0..1 (data coverage x closeness of the
satellite pass x how clear-cut the water share is). It is NOT a calibrated probability.
Reason text comes from fixed templates and only restates computed values.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from .. import config
from .geometry import Ring, plot_from_center, points_in_polygon, validate_ring
from .layer import FloodLayer, get_default_layer

FLOODED = "FLOODED"
PARTIALLY_FLOODED = "PARTIALLY_FLOODED"
NOT_FLOODED = "NOT_FLOODED"
PERMANENTLY_WET = "PERMANENTLY_WET"
INCONCLUSIVE = "INCONCLUSIVE"

REASON_TEMPLATES = {
    "water_share": ("Satellite pass on {obs_date} ({gap_days} day(s) from the claimed date) shows "
                    "{flooded_pct}% of the plot's normally-dry area under water."),
    "permanently_wet": "The plot lies on normally wet land (permanent water) and is excluded from flood evidence.",
    "no_nearby_observation": "No satellite pass within {max_gap} days of the claimed date.",
    "outside_layer": "The plot is outside the area covered by the flood layer.",
    "low_valid_coverage": "Satellite data over the plot is incomplete on {obs_date}.",
    "plot_too_small": "The plot is too small for the satellite resolution.",
}


@dataclass
class FloodResult:
    plot_id: Optional[str]
    query_date: str
    verdict: str
    flooded: Optional[bool]          # True / False / None (inconclusive)
    confidence: float                # heuristic 0..1, see module docstring
    reason_code: str
    reason: str
    flooded_fraction: Optional[float] = None
    permanent_water_fraction: Optional[float] = None
    valid_fraction: Optional[float] = None
    observation_date: Optional[str] = None
    days_gap: Optional[int] = None
    pixels_total: int = 0
    pixels_used: int = 0
    layer_id: Optional[str] = None
    layer_event: Optional[str] = None
    layer_is_synthetic: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def to_date(value: Union[str, date, datetime]) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError as exc:
        raise ValueError(f"date must look like 2021-07-22, got {value!r}") from exc


def normalize_plot(plot: Any) -> Tuple[Optional[str], Ring]:
    """Accepts: [[lon,lat],...] | {"polygon": [...]} | GeoJSON Polygon/Feature | {"lat","lon","area_sq_m"}."""
    plot_id = None
    if isinstance(plot, dict):
        plot_id = plot.get("plot_id") or plot.get("id")
        if plot.get("type") == "Feature":
            plot = plot.get("geometry") or {}
        if plot.get("type") == "Polygon":
            return plot_id, validate_ring(plot["coordinates"][0])
        if plot.get("polygon"):
            return plot_id, validate_ring(plot["polygon"])
        if plot.get("coordinates"):
            return plot_id, validate_ring(plot["coordinates"])
        if all(k in plot and plot[k] is not None for k in ("lat", "lon", "area_sq_m")):
            return plot_id, plot_from_center(float(plot["lat"]), float(plot["lon"]), float(plot["area_sq_m"]))
        raise ValueError("plot needs a polygon, or lat + lon + area_sq_m")
    return None, validate_ring(plot)


def _plot_pixels(layer: FloodLayer, ring: Ring):
    """Pixel grid covering the polygon's bounding box + mask of pixels whose centre is inside it."""
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    j0 = int(math.floor((min(lons) - layer.lon_min) / layer.res))
    j1 = int(math.floor((max(lons) - layer.lon_min) / layer.res))
    i0 = int(math.floor((layer.lat_max - max(lats)) / layer.res))
    i1 = int(math.floor((layer.lat_max - min(lats)) / layer.res))
    if (i1 - i0 + 1) * (j1 - j0 + 1) > config.MAX_PLOT_PIXEL_BOX:
        raise ValueError("polygon is too large")
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
    lon_c = layer.lon_min + (jj + 0.5) * layer.res
    lat_c = layer.lat_max - (ii + 0.5) * layer.res
    inside = points_in_polygon(lon_c, lat_c, ring)
    return ii, jj, inside


class FloodChecker:
    def __init__(self, layer: Optional[FloodLayer] = None):
        self.layer = layer if layer is not None else get_default_layer()

    def _result(self, plot_id, qdate, verdict, flooded, confidence, code, **kw) -> FloodResult:
        reason_values = {k: kw.pop(k) for k in ("max_gap", "obs_date", "gap_days", "flooded_pct") if k in kw}
        meta = self.layer.meta
        return FloodResult(
            plot_id=plot_id, query_date=qdate.isoformat(), verdict=verdict, flooded=flooded,
            confidence=round(float(confidence), 3), reason_code=code,
            reason=REASON_TEMPLATES[code].format(**reason_values),
            layer_id=meta.get("layer_id"), layer_event=meta.get("event_name"),
            layer_is_synthetic=bool(meta.get("is_synthetic", False)), **kw)

    def was_plot_flooded(self, plot: Any, on_date: Union[str, date, datetime],
                         plot_id: Optional[str] = None) -> FloodResult:
        layer = self.layer
        qdate = to_date(on_date)
        pid, ring = normalize_plot(plot)
        pid = plot_id or pid
        ii, jj, inside = _plot_pixels(layer, ring)
        total = int(inside.sum())

        if total < config.MIN_PLOT_PIXELS:
            return self._result(pid, qdate, INCONCLUSIVE, None, 0.0, "plot_too_small", pixels_total=total)

        in_layer = (ii >= 0) & (ii < layer.height) & (jj >= 0) & (jj < layer.width)
        sel = inside & in_layer
        if not sel.any():
            return self._result(pid, qdate, INCONCLUSIVE, None, 0.0, "outside_layer", pixels_total=total)
        si, sj = ii[sel], jj[sel]

        perm = layer.permanent[si, sj]
        perm_n = int(perm.sum())
        perm_frac = perm_n / total
        nonperm_total = total - perm_n

        if nonperm_total == 0:   # whole plot is normally wet
            return self._result(pid, qdate, PERMANENTLY_WET, False, perm_frac, "permanently_wet",
                                permanent_water_fraction=round(perm_frac, 3),
                                pixels_total=total, pixels_used=0, flooded_fraction=0.0)

        near = layer.nearest_observation(qdate)
        if near is None or near[1] > config.MAX_DAYS_GAP:
            return self._result(pid, qdate, INCONCLUSIVE, None, 0.0, "no_nearby_observation",
                                max_gap=config.MAX_DAYS_GAP, permanent_water_fraction=round(perm_frac, 3),
                                pixels_total=total)
        t, gap = near
        obs_date = layer.dates[t].isoformat()

        eligible = ~perm
        used = layer.valid[t][si, sj] & eligible
        used_n = int(used.sum())
        valid_frac = used_n / nonperm_total
        common = dict(observation_date=obs_date, days_gap=gap, pixels_total=total, pixels_used=used_n,
                      permanent_water_fraction=round(perm_frac, 3), valid_fraction=round(valid_frac, 3))
        if used_n == 0 or valid_frac < config.MIN_VALID_FRACTION:
            return self._result(pid, qdate, INCONCLUSIVE, None, 0.0, "low_valid_coverage",
                                obs_date=obs_date, **common)

        flooded_n = int((layer.water[t][si, sj] & used).sum())
        frac = flooded_n / used_n

        if frac >= config.FLOODED_MIN_FRACTION:
            verdict, flag = FLOODED, True
            decisive = 0.7 + 0.3 * (frac - config.FLOODED_MIN_FRACTION) / (1 - config.FLOODED_MIN_FRACTION)
        elif frac <= config.NOT_FLOODED_MAX_FRACTION:
            verdict, flag = NOT_FLOODED, False
            decisive = 0.7 + 0.3 * (config.NOT_FLOODED_MAX_FRACTION - frac) / config.NOT_FLOODED_MAX_FRACTION
        else:
            verdict, flag, decisive = PARTIALLY_FLOODED, True, 0.5
        temporal = 1.0 - gap / (config.MAX_DAYS_GAP + 1)
        confidence = max(0.0, min(1.0, temporal * valid_frac * decisive))

        return self._result(pid, qdate, verdict, flag, confidence, "water_share",
                            obs_date=obs_date, gap_days=gap, flooded_pct=f"{frac * 100:.0f}",
                            flooded_fraction=round(frac, 3), **common)


def was_plot_flooded(plot: Any, on_date: Union[str, date, datetime],
                     layer: Optional[FloodLayer] = None, plot_id: Optional[str] = None) -> dict:
    """One-call convenience for the pipeline: returns ``FloodResult`` as a plain dict."""
    return FloodChecker(layer).was_plot_flooded(plot, on_date, plot_id=plot_id).to_dict()
