from __future__ import annotations

from typing import List

from ..config import load_thresholds
from ..schemas import ClaimBundle, Reason, Recommendation
from .reasons import make
from .summary import build_summary

KEY_MATCHES = ("owner", "survey")


def _dedupe(reasons: List[Reason]) -> List[Reason]:
    seen, out = set(), []
    for r in reasons:
        if (r.code, r.text) not in seen:
            seen.add((r.code, r.text))
            out.append(r)
    return out


def recommend(bundle: ClaimBundle) -> Recommendation:
    cfg = load_thresholds()
    ecfg, fcfg = cfg["extraction"], cfg["flood"]
    red: List[Reason] = []
    amber: List[Reason] = []
    green: List[Reason] = []

    for err in bundle.service_errors:
        amber.append(make("SERVICE_UNAVAILABLE", service=err))

    ext = bundle.extraction
    if not ext.is_land_record:
        red.append(make("NOT_LAND_RECORD"))
    if not ext.quality.ok:
        amber.append(make("QUALITY_POOR", detail=ext.quality.message or ext.quality.code or "poor quality"))
    else:
        by_name = {f.name: f for f in ext.fields}
        for name in ecfg["key_fields"]:
            f = by_name.get(name)
            if f is None or f.value is None:
                amber.append(make("FIELD_MISSING", field=name))
            elif f.confidence < ecfg["min_field_confidence"]:
                amber.append(make("LOW_CONFIDENCE", field=name, pct=round(f.confidence * 100)))

        seen = set()
        for m in bundle.matches:
            seen.add(m.field)
            if m.status == "match":
                if m.field in KEY_MATCHES:
                    green.append(make(f"{m.field.upper()}_MATCH"))
            elif m.status == "possible":
                amber.append(make("MATCH_POSSIBLE", field=m.field, detail=m.detail or ""))
            elif m.status == "mismatch":
                target = red if m.field in KEY_MATCHES else amber
                target.append(make("MATCH_FAILED", field=m.field, detail=m.detail or ""))
            else:
                amber.append(make("FIELD_MISSING", field=m.field))
        for k in KEY_MATCHES:
            if k not in seen:
                amber.append(make("MATCH_NOT_RUN", field=k))

    if bundle.duplicate.found:
        red.append(make("DUPLICATE", claim_id=bundle.duplicate.claim_id or "an earlier claim"))
    else:
        green.append(make("NO_DUPLICATE"))

    r = bundle.rule
    kw = dict(rule_id=r.rule_id or "?", clause=r.clause or "?")
    if r.status == "eligible":
        green.append(make("RULE_OK", **kw))
    elif r.status == "not_eligible":
        red.append(make("RULE_NOT_ELIGIBLE", **kw))
    else:
        amber.append(make("RULE_NEEDS_REVIEW", **kw))

    fl = bundle.flood
    if fl.indicated is None or fl.confidence == "UNAVAILABLE":
        amber.append(make("FLOOD_UNAVAILABLE"))
    elif fl.indicated:
        if fl.confidence in fcfg["green_requires"]:
            green.append(make("FLOOD_INDICATED", confidence=fl.confidence, date=fl.image_date or "n/a"))
        else:
            amber.append(make("FLOOD_INDICATED_LOW", confidence=fl.confidence))
    else:
        if fl.confidence in fcfg["red_if_not_indicated_at"]:
            red.append(make("FLOOD_NOT_INDICATED", confidence=fl.confidence))
        else:
            amber.append(make("FLOOD_NOT_INDICATED_UNSURE", confidence=fl.confidence))

    red, amber, green = _dedupe(red), _dedupe(amber), _dedupe(green)
    lane = "RED" if red else "AMBER" if amber else "GREEN"
    problems = red + amber
    ordered = green if lane == "GREEN" else problems + green
    return Recommendation(
        lane=lane,
        reasons=ordered[: cfg["recommend"]["max_reasons"]],
        summary=build_summary(lane, bundle, problems),
        flags=[p.code for p in problems],
    )
