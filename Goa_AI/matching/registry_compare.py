"""Compare what we read from the document with the land registry record."""
from __future__ import annotations

from typing import List

from rapidfuzz import fuzz

from ..config import load_thresholds
from ..documents.validate import normalize_name, normalize_place, normalize_survey
from ..schemas import ExtractionResult, MatchResult


def compare_with_registry(extraction: ExtractionResult, registry: dict) -> List[MatchResult]:
    """registry keys: owner (or owners list), survey, area_ha, village, taluka.
    A key missing from the registry is simply not compared."""
    cfg = load_thresholds()["matching"]
    got = {f.name: f.value for f in extraction.fields}
    results: List[MatchResult] = []

    owners = registry.get("owners") or ([registry["owner"]] if registry.get("owner") else [])
    if owners:
        v = got.get("owner")
        if v is None:
            results.append(MatchResult(field="owner", status="missing", registry=owners[0]))
        else:
            score, best = max((fuzz.token_sort_ratio(normalize_name(v), normalize_name(o)), o) for o in owners)
            status = ("match" if score >= cfg["name_match_score"]
                      else "possible" if score >= cfg["name_possible_score"] else "mismatch")
            results.append(MatchResult(field="owner", status=status, extracted=v, registry=best,
                                       detail=f"closest registry name scored {score:.0f}/100"))

    if registry.get("survey") is not None:
        v = got.get("survey")
        if v is None:
            results.append(MatchResult(field="survey", status="missing", registry=registry["survey"]))
        else:
            ok = normalize_survey(v) == normalize_survey(registry["survey"])
            results.append(MatchResult(field="survey", status="match" if ok else "mismatch",
                                       extracted=v, registry=registry["survey"],
                                       detail=None if ok else "survey numbers differ"))

    if registry.get("area_ha") is not None:
        v = got.get("area_ha")
        r = float(registry["area_ha"])
        if v is None:
            results.append(MatchResult(field="area_ha", status="missing", registry=r))
        else:
            pct = abs(float(v) - r) / r * 100 if r else 0.0
            tol = cfg["area_tolerance_pct"]
            status = "match" if pct <= tol else "possible" if pct <= 2 * tol else "mismatch"
            results.append(MatchResult(field="area_ha", status=status, extracted=float(v), registry=r,
                                       detail=f"Area differs from registry by {pct:.1f}%"))

    for name in ("village", "taluka"):
        if registry.get(name) is None:
            continue
        v = got.get(name)
        if v is None:
            results.append(MatchResult(field=name, status="missing", registry=registry[name]))
            continue
        a, b = normalize_place(v), normalize_place(registry[name])
        if a == b:
            status = "match"
        elif fuzz.ratio(a, b) >= 85:
            status = "possible"
        else:
            status = "mismatch"
        results.append(MatchResult(field=name, status=status, extracted=v, registry=registry[name]))
    return results
