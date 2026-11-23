
import pytest
from pydantic import ValidationError

from rules.schemas import CalculationRequest


def flood_request():
    return {
        "claim_id": "GOA-001",
        "scheme": "flood_relief",
        "incident_date": "2026-06-15",
        "flood_relief": {
            "eligible_area": {
                "value": "1.2500",
                "unit": "hectare",
            }
        },
    }


def land_request():
    return {
        "claim_id": "GOA-002",
        "scheme": "land_acquisition",
        "incident_date": "2026-06-15",
        "land_acquisition": {
            "land_value": "100000",
            "structures": [
                {
                    "description": "House",
                    "value": "20000",
                }
            ],
            "trees": [],
            "interest_start_date": "2026-01-01",
            "interest_end_date": "2026-12-31",
        },
    }


def test_valid_flood_calculation_request():
    request = CalculationRequest.model_validate(
        flood_request()
    )

    assert request.scheme == "flood_relief"


def test_valid_land_calculation_request():
    request = CalculationRequest.model_validate(
        land_request()
    )

    assert request.scheme == "land_acquisition"


def test_flood_request_requires_flood_inputs():
    data = flood_request()
    del data["flood_relief"]

    with pytest.raises(ValidationError):
        CalculationRequest.model_validate(data)


def test_land_request_requires_land_inputs():
    data = land_request()
    del data["land_acquisition"]

    with pytest.raises(ValidationError):
        CalculationRequest.model_validate(data)


def test_flood_request_rejects_land_inputs():
    data = flood_request()
    data["land_acquisition"] = land_request()["land_acquisition"]

    with pytest.raises(ValidationError):
        CalculationRequest.model_validate(data)


def test_land_request_rejects_flood_inputs():
    data = land_request()
    data["flood_relief"] = flood_request()["flood_relief"]

    with pytest.raises(ValidationError):
        CalculationRequest.model_validate(data)


def test_negative_land_value_is_rejected():
    data = land_request()
    data["land_acquisition"]["land_value"] = "-100"

    with pytest.raises(ValidationError):
        CalculationRequest.model_validate(data)


def test_decimal_values_must_be_strings():
    data = flood_request()
    data["flood_relief"]["eligible_area"]["value"] = 1.25

    with pytest.raises(ValidationError):
        CalculationRequest.model_validate(data)
