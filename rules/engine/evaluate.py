
from typing import Any

from rules.schemas import EvaluateRequest
from rules.engine.loader import load_rule_pack


def evaluate_claim(request: EvaluateRequest) -> dict[str, Any]:
    """
    Evaluate claim evidence and identify conditions requiring officer review.

    This demo implementation does NOT make a final legal eligibility decision.
    """

    pack = load_rule_pack(
        scheme=request.scheme,
        version=request.rule_version,
        incident_date=request.incident_date,
    )

    facts = request.facts
    conditions = []

    def add_condition(
        rule_id: str,
        title: str,
        status: str,
        reason: str,
        inputs_used: dict[str, Any],
    ) -> None:
        conditions.append({
            "rule_id": rule_id,
            "title": title,
            "status": status,
            "reason": reason,
            "clause": None,
            "source_document": None,
            "inputs_used": inputs_used,
        })

    # 1. Document verification
    if facts.documents_verified is True:
        add_condition(
            "DOC-001",
            "Document verification",
            "passed",
            "Documents are marked as verified by the upstream workflow.",
            {"documents_verified": True},
        )
    else:
        add_condition(
            "DOC-001",
            "Document verification",
            "review_required",
            "Documents are missing or have not been verified.",
            {"documents_verified": facts.documents_verified},
        )

    # 2. Land registry matching
    if facts.registry_match is True:
        add_condition(
            "REG-001",
            "Land registry matching",
            "passed",
            "The upstream registry check reports a match.",
            {"registry_match": True},
        )
    else:
        add_condition(
            "REG-001",
            "Land registry matching",
            "review_required",
            "Registry matching is incomplete or requires officer verification.",
            {"registry_match": facts.registry_match},
        )

    # 3. Duplicate claim screening
    if facts.duplicate_status == "clear":
        add_condition(
            "DUP-001",
            "Duplicate claim screening",
            "passed",
            "The upstream duplicate screening reports no duplicate.",
            {"duplicate_status": "clear"},
        )
    else:
        add_condition(
            "DUP-001",
            "Duplicate claim screening",
            "review_required",
            "Duplicate screening is incomplete or has identified a possible or confirmed duplicate.",
            {"duplicate_status": facts.duplicate_status},
        )

    # 4. Flood evidence is supporting evidence only.
    if facts.flood_evidence is None:
        add_condition(
            "FLD-001",
            "Flood evidence availability",
            "review_required",
            "No flood evidence was supplied.",
            {"flood_evidence": None},
        )
    elif facts.flood_evidence.status == "uncertain":
        add_condition(
            "FLD-001",
            "Flood evidence availability",
            "review_required",
            "Flood evidence is uncertain and requires officer review.",
            {
                "status": facts.flood_evidence.status,
                "overlap_percent": (
                    str(facts.flood_evidence.overlap_percent)
                    if facts.flood_evidence.overlap_percent is not None
                    else None
                ),
            },
        )
    else:
        add_condition(
            "FLD-001",
            "Flood evidence availability",
            "passed",
            "Flood evidence was supplied. It is supporting evidence, not proof of crop damage or eligibility.",
            {
                "status": facts.flood_evidence.status,
                "overlap_percent": (
                    str(facts.flood_evidence.overlap_percent)
                    if facts.flood_evidence.overlap_percent is not None
                    else None
                ),
            },
        )

    # 5. Eligible land area availability
    if facts.eligible_area is None:
        add_condition(
            "AREA-001",
            "Eligible land area availability",
            "review_required",
            "Eligible land area has not been supplied by the upstream workflow.",
            {"eligible_area": None},
        )
    else:
        add_condition(
            "AREA-001",
            "Eligible land area availability",
            "passed",
            "Eligible land area was supplied by the upstream workflow.",
            {
                "value": str(facts.eligible_area.value),
                "unit": facts.eligible_area.unit,
            },
        )

    # The demo pack contains no verified legal eligibility rules.
    # Therefore, an officer must review the claim.
    overall_status = (
        "review_required"
        if pack["status"] == "demo"
        or any(
            condition["status"] == "review_required"
            for condition in conditions
        )
        else "passed"
    )

    notices = []

    if pack["status"] == "demo":
        notices.append(
            "DEMO RULE PACK: No official eligibility determination "
            "or government compensation policy is implemented."
        )

    notices.append(
        "AI-assisted evidence screening does not replace the "
        "authorised officer's decision."
    )

    return {
        "claim_id": request.claim_id,
        "scheme": request.scheme,
        "overall_status": overall_status,
        "conditions": conditions,
        "rule_pack": {
            "scheme": pack["scheme"],
            "version": pack["version"],
            "status": pack["status"],
            "sha256": pack["_sha256"],
        },
        "notices": notices,
    }
