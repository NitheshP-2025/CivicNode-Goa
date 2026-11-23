from __future__ import annotations

import re
from typing import List

from ..schemas import ClaimBundle, Reason

LANE_SENTENCE = {
    "GREEN": "Documents match the registry and the automated checks passed.",
    "AMBER": "This claim needs a closer look before a decision.",
    "RED": "This claim has a serious mismatch or flag and needs careful review.",
}

PROBLEM_PHRASES = {
    "FIELD_MISSING": "some fields could not be read",
    "LOW_CONFIDENCE": "some fields were read with low confidence",
    "MATCH_FAILED": "details do not match the registry",
    "MATCH_POSSIBLE": "some details may not match the registry",
    "MATCH_NOT_RUN": "registry comparison is incomplete",
    "QUALITY_POOR": "the document quality is poor",
    "NOT_LAND_RECORD": "the file does not look like a land record",
    "DUPLICATE": "a possible duplicate claim was found",
    "RULE_NOT_ELIGIBLE": "the claim does not meet the relief rule",
    "RULE_NEEDS_REVIEW": "the rule check needs review",
    "FLOOD_INDICATED_LOW": "flood evidence is weak",
    "FLOOD_NOT_INDICATED": "satellite data does not indicate flooding",
    "FLOOD_NOT_INDICATED_UNSURE": "satellite data does not clearly indicate flooding",
    "FLOOD_UNAVAILABLE": "satellite evidence is unavailable",
    "SERVICE_UNAVAILABLE": "a check could not be completed",
}

CLOSING = "Damage is to be confirmed by the officer."
_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def numbers_in(text: str) -> set:
    return set(_NUM.findall(text))


def build_summary(lane: str, bundle: ClaimBundle, problems: List[Reason]) -> str:
    parts = [LANE_SENTENCE[lane]]

    phrases: List[str] = []
    for r in problems:
        p = PROBLEM_PHRASES.get(r.code)
        if p and p not in phrases:
            phrases.append(p)
    if phrases:
        parts.append("Points to check: " + "; ".join(phrases[:3]) + ".")

    fl = bundle.flood
    if fl.indicated is True and fl.confidence != "UNAVAILABLE":
        when = f", image date {fl.image_date}" if fl.image_date else ""
        parts.append(f"Satellite data indicates flooding over this plot ({fl.confidence} confidence{when}).")
    elif fl.indicated is False and fl.confidence != "UNAVAILABLE":
        parts.append(f"Satellite data does not indicate flooding ({fl.confidence} confidence).")
    else:
        parts.append("Satellite evidence is unavailable.")

    if bundle.rule.rule_id:
        parts.append(f"Rule applied: {bundle.rule.rule_id}.")
    if bundle.calculation and bundle.calculation.total:
        parts.append(f"Calculated amount: ₹{bundle.calculation.total} (from the calculator).")
    parts.append(CLOSING)

    text = " ".join(parts)
    if numbers_in(text) - numbers_in(bundle.model_dump_json()):
        return f"{LANE_SENTENCE[lane]} {CLOSING}"
    return text
