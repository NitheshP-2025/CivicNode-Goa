
import pytest
from pydantic import ValidationError

from rules.schemas import EvaluateRequest


def valid_request():
    return {
        "claim_id": "GOA-CLAIM-001",
        "scheme": "flood_relief",
        "incident_date": "2026-06-15",
        "facts": {
            "survey_number": "SUR-101",
            "eligible_area": {
                "value": "1.2500",
                "unit": "hectare",
            },
            "registry_match": True,
            "flood_evidence": {
                "status": "flooded",
                "overlap_percent": "75.50",
            },
            "duplicate_status": "clear",
            "documents_verified": True,
        },
    }


def test_valid_evaluation_request():
    request = EvaluateRequest.model_validate(valid_request())

    assert request.claim_id == "GOA-CLAIM-001"
    assert request.scheme == "flood_relief"
    assert request.facts.eligible_area.value == 1.2500


def test_missing_claim_id_is_rejected():
    data = valid_request()
    del data["claim_id"]

    with pytest.raises(ValidationError):
        EvaluateRequest.model_validate(data)


def test_invalid_scheme_is_rejected():
    data = valid_request()
    data["scheme"] = "unknown_scheme"

    with pytest.raises(ValidationError):
        EvaluateRequest.model_validate(data)


def test_decimal_must_be_a_string():
    data = valid_request()
    data["facts"]["eligible_area"]["value"] = 1.25

    with pytest.raises(ValidationError):
        EvaluateRequest.model_validate(data)


def test_unknown_fields_are_rejected():
    data = valid_request()
    data["unexpected_field"] = "not allowed"

    with pytest.raises(ValidationError):
        EvaluateRequest.model_validate(data)


def test_flood_overlap_cannot_exceed_100():
    data = valid_request()
    data["facts"]["flood_evidence"]["overlap_percent"] = "105"

    with pytest.raises(ValidationError):
        EvaluateRequest.model_validate(data)
