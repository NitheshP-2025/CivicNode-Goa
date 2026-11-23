"""Small geometry helpers (no GIS dependency)."""
from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import numpy as np

Ring = List[Tuple[float, float]]  # [(lon, lat), ...]

_M_PER_DEG_LAT = 110_574.0
_M_PER_DEG_LON_EQ = 111_320.0


def validate_ring(ring: Sequence[Sequence[float]]) -> Ring:
    pts: Ring = []
    for p in ring:
        if len(p) < 2:
            raise ValueError("each polygon point needs [lon, lat]")
        lon, lat = float(p[0]), float(p[1])
        if not (math.isfinite(lon) and math.isfinite(lat)):
            raise ValueError("polygon contains a non-finite coordinate")
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("coordinates must be [lon, lat] within valid ranges")
        pts.append((lon, lat))
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts.pop()
    if len(pts) < 3:
        raise ValueError("polygon needs at least 3 distinct points")
    return pts


def polygon_area_sq_m(ring: Sequence[Sequence[float]]) -> float:
    pts = validate_ring(ring)
    lat0 = sum(p[1] for p in pts) / len(pts)
    kx = _M_PER_DEG_LON_EQ * math.cos(math.radians(lat0))
    xy = [(p[0] * kx, p[1] * _M_PER_DEG_LAT) for p in pts]
    s = 0.0
    for (x1, y1), (x2, y2) in zip(xy, xy[1:] + xy[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def plot_from_center(lat: float, lon: float, area_sq_m: float) -> Ring:
    """Square polygon of the given area centred on a point (when only a centroid is known)."""
    if not (area_sq_m > 0 and math.isfinite(area_sq_m)):
        raise ValueError("area_sq_m must be a positive number")
    side = math.sqrt(area_sq_m)
    half_lat = side / 2 / _M_PER_DEG_LAT
    cos_lat = math.cos(math.radians(lat))
    if cos_lat <= 0:
        raise ValueError("latitude too close to a pole")
    half_lon = side / 2 / (_M_PER_DEG_LON_EQ * cos_lat)
    return validate_ring([
        (lon - half_lon, lat - half_lat), (lon + half_lon, lat - half_lat),
        (lon + half_lon, lat + half_lat), (lon - half_lon, lat + half_lat)])


def points_in_polygon(xs: np.ndarray, ys: np.ndarray, ring: Ring) -> np.ndarray:
    """Vectorised ray casting. ``xs``/``ys`` share a shape; returns a bool array."""
    inside = np.zeros(xs.shape, dtype=bool)
    n = len(ring)
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in range(n):
            x1, y1 = ring[k]
            x2, y2 = ring[(k + 1) % n]
            crosses = (y1 > ys) != (y2 > ys)
            x_at = (x2 - x1) * (ys - y1) / (y2 - y1) + x1
            inside ^= crosses & (xs < x_at)
    return inside
