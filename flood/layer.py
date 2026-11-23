"""The precomputed satellite flood layer.

A layer is a stack of water masks, one per satellite pass, on a regular
lon/lat grid, plus a mask of land that is *normally* wet (rivers, lakes) so
that permanent water is never counted as flood damage.

Build one:
    python -m civicnode_ai2.flood.layer --demo --out data/flood/goa_demo_layer.npz
or from real Sentinel-1 GeoTIFFs: see ``build_layer_from_sar_geotiffs`` and docs/EARTH_ENGINE.md.

The DEMO layer is synthetic and says so in its metadata. Never present it as
real satellite evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from .. import config


@dataclass
class FloodLayer:
    lon_min: float
    lat_max: float
    res: float                 # pixel size in degrees (square pixels)
    dates: List[date]          # one per observation, ascending
    water: np.ndarray          # (T, H, W) bool - open water seen on that pass
    valid: np.ndarray          # (T, H, W) bool - pixel was actually observed
    permanent: np.ndarray      # (H, W) bool - normally wet land
    meta: Dict = field(default_factory=dict)

    def __post_init__(self):
        if self.res <= 0:
            raise ValueError("res must be positive")
        if self.water.ndim != 3 or self.water.shape != self.valid.shape:
            raise ValueError("water and valid must both have shape (T, H, W)")
        if self.permanent.shape != self.water.shape[1:]:
            raise ValueError("permanent must have shape (H, W)")
        if len(self.dates) != self.water.shape[0]:
            raise ValueError("need exactly one date per observation")
        if list(self.dates) != sorted(self.dates):
            raise ValueError("dates must be ascending")
        self.water = self.water.astype(bool, copy=False)
        self.valid = self.valid.astype(bool, copy=False)
        self.permanent = self.permanent.astype(bool, copy=False)

    # ---- geometry
    @property
    def height(self) -> int:
        return self.water.shape[1]

    @property
    def width(self) -> int:
        return self.water.shape[2]

    @property
    def lat_min(self) -> float:
        return self.lat_max - self.height * self.res

    @property
    def lon_max(self) -> float:
        return self.lon_min + self.width * self.res

    def ij_to_lonlat(self, i: float, j: float) -> Tuple[float, float]:
        """Centre of pixel (row i, col j) as (lon, lat)."""
        return self.lon_min + (j + 0.5) * self.res, self.lat_max - (i + 0.5) * self.res

    def lonlat_to_ij(self, lon: float, lat: float) -> Tuple[int, int]:
        return (int(math.floor((self.lat_max - lat) / self.res)),
                int(math.floor((lon - self.lon_min) / self.res)))

    # ---- observations
    def nearest_observation(self, on_date: date) -> Optional[Tuple[int, int]]:
        """(index, gap_in_days) of the pass closest to ``on_date`` (ties -> earlier)."""
        if not self.dates:
            return None
        best = min(range(len(self.dates)), key=lambda k: (abs((self.dates[k] - on_date).days), self.dates[k]))
        return best, abs((self.dates[best] - on_date).days)

    # ---- info / io
    def info(self) -> dict:
        return {
            "layer_id": self.meta.get("layer_id"),
            "event_name": self.meta.get("event_name"),
            "source": self.meta.get("source"),
            "is_synthetic": bool(self.meta.get("is_synthetic", False)),
            "bbox": {"lon_min": self.lon_min, "lat_min": self.lat_min,
                     "lon_max": self.lon_max, "lat_max": self.lat_max},
            "pixel_size_deg": self.res,
            "size": {"height": self.height, "width": self.width},
            "observation_dates": [d.isoformat() for d in self.dates],
            "notes": self.meta.get("notes"),
        }

    def save(self, path: Union[str, Path]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path, water=self.water, valid=self.valid, permanent=self.permanent,
            dates=np.array([d.isoformat() for d in self.dates]),
            geo=np.array([self.lon_min, self.lat_max, self.res], dtype=np.float64),
            meta=np.array(json.dumps(self.meta)))
        return path

    @classmethod
    def load(cls, path: Union[str, Path]) -> "FloodLayer":
        with np.load(Path(path), allow_pickle=False) as z:
            lon_min, lat_max, res = (float(v) for v in z["geo"])
            return cls(lon_min=lon_min, lat_max=lat_max, res=res,
                       dates=[date.fromisoformat(str(d)) for d in z["dates"]],
                       water=z["water"], valid=z["valid"], permanent=z["permanent"],
                       meta=json.loads(str(z["meta"])))


# ---------------------------------------------------------------------------
# Demo (synthetic) layer
# ---------------------------------------------------------------------------
DEMO_BBOX = (74.10, 15.50, 74.18, 15.57)   # lon_min, lat_min, lon_max, lat_max
DEMO_RES = 0.0001                          # about 11 m
DEMO_W, DEMO_H = 800, 700
DEMO_RIVER_HALF_WIDTH = 12                 # pixels
_DEMO_DATES = [date(2021, 7, 10), date(2021, 7, 16), date(2021, 7, 22), date(2021, 7, 28)]
_DEMO_FLOOD_HALF_WIDTH = {0: DEMO_RIVER_HALF_WIDTH, 1: 44, 2: 90, 3: 56}   # per date index
DEMO_INVALID_PATCH = (520, 600, 360, 440)  # rows lo, hi, cols lo, hi - missing data on the last pass


def demo_river_row(col) -> np.ndarray:
    """Row of the demo river centre line at column(s) ``col``."""
    return DEMO_H * 0.5 + 60 * np.sin(2 * np.pi * np.asarray(col, dtype=float) * 1.5 / DEMO_W)


def build_demo_layer() -> FloodLayer:
    """Synthetic river valley that floods, peaks on 2021-07-22 and recedes."""
    rows = np.arange(DEMO_H, dtype=float)[:, None]
    dist = np.abs(rows - demo_river_row(np.arange(DEMO_W))[None, :])
    water = np.stack([dist <= _DEMO_FLOOD_HALF_WIDTH[k] for k in range(len(_DEMO_DATES))])
    valid = np.ones_like(water, dtype=bool)
    r0, r1, c0, c1 = DEMO_INVALID_PATCH
    valid[3, r0:r1, c0:c1] = False
    water[3, r0:r1, c0:c1] = False
    permanent = dist <= DEMO_RIVER_HALF_WIDTH
    return FloodLayer(
        lon_min=DEMO_BBOX[0], lat_max=DEMO_BBOX[3], res=DEMO_RES, dates=list(_DEMO_DATES),
        water=water, valid=valid, permanent=permanent,
        meta={"layer_id": "demo-synthetic-v1",
              "event_name": "DEMO (synthetic) river-valley flood, July 2021 style",
              "source": "synthetic - generated by civicnode_ai2.flood.layer.build_demo_layer",
              "is_synthetic": True,
              "notes": "NOT real satellite data. Replace with a layer built from Sentinel-1 for the demo."})


# ---------------------------------------------------------------------------
# Real data: Sentinel-1 GeoTIFFs (dB, VV) exported e.g. from Google Earth Engine
# ---------------------------------------------------------------------------
def water_from_sar_db(db: np.ndarray, threshold_db: float = config.SAR_WATER_THRESHOLD_DB):
    """Open water is dark in SAR: returns (water, valid) boolean masks."""
    valid = np.isfinite(db)
    water = np.zeros(db.shape, dtype=bool)
    water[valid] = db[valid] <= threshold_db
    return water, valid


def build_layer_from_sar_geotiffs(
        observations: Sequence[Tuple[date, Union[str, Path]]],
        baseline_dates: Sequence[date] = (),
        permanent_water_tif: Optional[Union[str, Path]] = None,
        permanent_min_occurrence: float = config.PERMANENT_WATER_MIN_OCCURRENCE,
        threshold_db: float = config.SAR_WATER_THRESHOLD_DB,
        event_name: str = "unnamed event",
        source: str = "Sentinel-1 GRD (VV)",
        out_path: Optional[Union[str, Path]] = None) -> FloodLayer:
    """Build a layer from single-band GeoTIFFs that share one EPSG:4326 north-up grid.

    ``observations``: (acquisition date, path) for every pass, baseline passes included.
    ``permanent_water_tif``: e.g. JRC Global Surface Water 'occurrence' (0-100) on the same grid.
    If omitted, land that is water in *every* baseline pass is treated as permanent water
    (so supply at least one date in ``baseline_dates``).
    """
    try:
        import rasterio
    except ImportError as exc:
        raise ImportError("pip install rasterio to build a layer from GeoTIFFs") from exc
    if not observations:
        raise ValueError("no observations given")
    if permanent_water_tif is None and not baseline_dates:
        raise ValueError("give permanent_water_tif or at least one baseline date")

    obs = sorted(((d, Path(p)) for d, p in observations), key=lambda x: x[0])
    ref = None
    waters, valids = [], []
    for d, p in obs:
        with rasterio.open(p) as src:
            if src.crs is None or src.crs.to_epsg() != 4326:
                raise ValueError(f"{p.name}: must be in EPSG:4326 (re-export with crs='EPSG:4326')")
            t = src.transform
            if t.b != 0 or t.d != 0 or t.e >= 0 or not math.isclose(t.a, -t.e, rel_tol=1e-3):
                raise ValueError(f"{p.name}: need a north-up grid with square pixels")
            if ref is None:
                ref = (src.shape, t)
            elif src.shape != ref[0] or not t.almost_equals(ref[1]):
                raise ValueError(f"{p.name}: grid differs from the first file; export all with the same region and scale")
            arr = src.read(1).astype("float32")
            if src.nodata is not None:
                arr[arr == src.nodata] = np.nan
        w, v = water_from_sar_db(arr, threshold_db)
        waters.append(w)
        valids.append(v)

    water, valid = np.stack(waters), np.stack(valids)
    dates = [d for d, _ in obs]

    if permanent_water_tif is not None:
        with rasterio.open(permanent_water_tif) as src:
            if src.shape != ref[0]:
                raise ValueError("permanent water raster must be on the same grid as the observations")
            occ = src.read(1).astype("float32")
        permanent = np.nan_to_num(occ, nan=0.0) >= permanent_min_occurrence
    else:
        idx = [k for k, d in enumerate(dates) if d in set(baseline_dates)]
        if not idx:
            raise ValueError("none of the baseline dates match an observation date")
        permanent = np.logical_and.reduce([water[k] & valid[k] for k in idx])

    transform = ref[1]
    layer = FloodLayer(
        lon_min=float(transform.c), lat_max=float(transform.f), res=float(transform.a),
        dates=dates, water=water, valid=valid, permanent=permanent,
        meta={"layer_id": f"sar-{dates[0].isoformat()}-{dates[-1].isoformat()}",
              "event_name": event_name, "source": source, "is_synthetic": False,
              "threshold_db": threshold_db,
              "notes": "Water = backscatter <= threshold. Hills, urban areas and vegetation can cause errors."})
    if out_path:
        layer.save(out_path)
    return layer


def get_default_layer(path: Optional[Union[str, Path]] = None) -> FloodLayer:
    """Load the configured layer; if none exists yet, create (and save) the synthetic demo one."""
    path = Path(path) if path else config.DEFAULT_LAYER_PATH
    if not path.exists():
        build_demo_layer().save(path)
    return FloodLayer.load(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the demo flood layer")
    ap.add_argument("--demo", action="store_true", help="write the synthetic demo layer")
    ap.add_argument("--out", default=str(config.DEFAULT_LAYER_PATH))
    args = ap.parse_args(argv)
    if not args.demo:
        ap.error("only --demo is available from the command line; use build_layer_from_sar_geotiffs() for real data")
    p = build_demo_layer().save(args.out)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
