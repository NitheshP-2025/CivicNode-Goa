"""Loads every tunable number from one YAML file (recommend/thresholds.yaml)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).parent / "recommend" / "thresholds.yaml"


@lru_cache(maxsize=1)
def load_thresholds() -> dict:
    path = Path(os.getenv("AI_THRESHOLDS_PATH", str(DEFAULT_PATH)))
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
