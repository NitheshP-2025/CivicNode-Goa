
import pytest

from rules.schemas import EvaluateRequest
from rules.engine.evaluate import evaluate_claim


def make_request(**fact_updates):
    facts = {
        "documents_verified": True,
        "registry_match": True,
        "duplicate_status": "clear",
        "flood_evidence": {
            "status": "flooded",
            "overlap_percent": "75.50",
        },
        "eligible_area": {
            "value": "1.2500",
            "unit": "hectare",
        },
    }

    facts.update(fact_updates)

    return EvaluateRequest.model_validate({
        "claim_id": "GOA-CLAIM-001",
        "scheme": "flood_relief",
        "incident_date": "2026-06-15",
        "rule_version": "v1",
        "facts": facts,
    })


def test_complete_claim_requires_officer_review():
    result = evaluate_claim(make_request())

    assert result["overall_status"] == "review_required"
    assert result["rule_pack"]["status"] == "demo"


def test_missing_documents_requires_review():
    result = evaluate_claim(
        make_request(documents_verified=None)
    )

    document_condition = result["conditions"][0]

    assert document_condition["status"] == "review_required"


def test_registry_mismatch_requires_review():
    result = evaluate_claim(
        make_request(registry_match=False)
    )

    registry_condition = result["conditions"][1]

    assert registry_condition["status"] == "review_required"


def test_possible_duplicate_requires_review():
    result = evaluate_claim(
        make_request(duplicate_status="possible_duplicate")
    )

    duplicate_condition = result["conditions"][2]

    assert duplicate_condition["status"] == "review_required"


def test_uncertain_flood_evidence_requires_review():
    result = evaluate_claim(
        make_request(
            flood_evidence={
                "status": "uncertain",
                "overlap_percent": "40.00",
            }
        )
    )

    flood_condition = result["conditions"][3]

    assert flood_condition["status"] == "review_required"


def test_flood_evidence_never_causes_automatic_rejection():
    result = evaluate_claim(
        make_request(
            flood_evidence={
                "status": "not_flooded",
                "overlap_percent": "0",
            }
        )
    )

    flood_condition = result["conditions"][3]

    assert flood_condition["status"] != "failed"


def test_missing_land_area_requires_review():
    result = evaluate_claim(
        make_request(eligible_area=None)
    )

    area_condition = result["conditions"][4]

    assert area_condition["status"] == "review_required"


def test_demo_notice_is_returned():
    result = evaluate_claim(make_request())

    assert any(
        "DEMO RULE PACK" in notice
        for notice in result["notices"]
    )


def test_explicit_version_rejected_when_not_effective_on_incident_date():
    from datetime import date
    from rules.errors import RulesServiceError

    request = EvaluateRequest.model_validate({
        "claim_id": "GOA-CLAIM-001",
        "scheme": "flood_relief",
        "incident_date": "2025-12-31",
        "rule_version": "v1",
        "facts": {
            "documents_verified": True,
            "registry_match": True,
            "duplicate_status": "clear",
            "flood_evidence": {
                "status": "flooded",
                "overlap_percent": "75.50",
            },
            "eligible_area": {
                "value": "1.2500",
                "unit": "hectare",
            },
        },
    })

    with pytest.raises(RulesServiceError) as exc:
        evaluate_claim(request)

    assert exc.value.code == "RULE_VERSION_NOT_EFFECTIVE"
    assert exc.value.status_code == 422
