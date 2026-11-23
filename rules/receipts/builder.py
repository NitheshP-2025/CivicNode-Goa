
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4


DEMO_DISCLAIMER = (
    "This receipt documents a synthetic demonstration "
    "calculation. It is not an official Government of Goa "
    "compensation order or proof of payment."
)

REVIEW_NOTICE = (
    "The calculation is advisory and requires authorised "
    "officer review."
)


def build_receipt(calculation_result: dict) -> dict:
    """
    Build a traceable receipt from a completed calculation.

    This function documents a calculation.
    It does not approve claims or authorise payments.
    """

    required_fields = {
        "claim_id",
        "scheme",
        "incident_date",
        "rule_pack",
        "calculation",
    }

    missing_fields = required_fields - calculation_result.keys()

    if missing_fields:
        raise ValueError(
            f"Missing calculation fields: {sorted(missing_fields)}"
        )

    rule_pack = calculation_result["rule_pack"]
    calculation = calculation_result["calculation"]

    if not isinstance(rule_pack, dict):
        raise ValueError("Invalid rule pack information.")

    if not isinstance(calculation, dict):
        raise ValueError("Invalid calculation information.")

    for field in ("version", "status", "sha256"):
        if not rule_pack.get(field):
            raise ValueError(
                f"Missing rule pack field: {field}"
            )

    if len(rule_pack["sha256"]) != 64:
        raise ValueError("Invalid SHA-256 hash.")

    receipt_id = f"RCP-{uuid4().hex[:12].upper()}"

    generated_at = (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )

    return {
        "receipt_id": receipt_id,
        "created_at": generated_at,
        "generated_at": generated_at,
        "claim_id": calculation_result["claim_id"],
        "scheme": calculation_result["scheme"],
        "incident_date": calculation_result["incident_date"],
        "receipt_status": "demonstration",
        "decision_status": "pending_officer_review",
        "rule_pack": deepcopy(rule_pack),
        "calculation": deepcopy(calculation),
        "notices": list(calculation_result.get("notices", []))
        + [DEMO_DISCLAIMER, REVIEW_NOTICE],
    }
