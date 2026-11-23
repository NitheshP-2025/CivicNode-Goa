
from datetime import date

from rules.schemas import (
    CalculationRequest,
    EligibleArea,
    FloodReliefInputs,
    LandAcquisitionInputs,
)
from rules.service import calculate_claim


def test_flood_relief_service():
    request = CalculationRequest(
        claim_id="CLM-FLOOD-001",
        scheme="flood_relief",
        incident_date=date(2026, 6, 15),
        flood_relief=FloodReliefInputs(
            eligible_area=EligibleArea(
                value="2",
                unit="hectare",
            )
        ),
    )

    result = calculate_claim(request)

    assert result["claim_id"] == "CLM-FLOOD-001"
    assert result["scheme"] == "flood_relief"
    assert result["rule_pack"]["version"] == "v1"
    assert result["rule_pack"]["status"] == "demo"
    assert len(result["rule_pack"]["sha256"]) == 64
    assert result["calculation"]["total"] == "2222.22"

def test_land_acquisition_service():
    request = CalculationRequest(
        claim_id="CLM-LAND-001",
        scheme="land_acquisition",
        incident_date=date(2026, 6, 15),
        land_acquisition=LandAcquisitionInputs(
            land_value="100000",
            structures=[],
            trees=[],
            interest_start_date=date(2026, 1, 1),
            interest_end_date=date(2027, 1, 1),
        ),
    )

    result = calculate_claim(request)

    assert result["claim_id"] == "CLM-LAND-001"
    assert result["scheme"] == "land_acquisition"
    assert result["rule_pack"]["version"] == "v1"
    assert result["rule_pack"]["status"] == "demo"
    assert len(result["rule_pack"]["sha256"]) == 64


def test_calculation_returns_demo_notices():
    request = CalculationRequest(
        claim_id="CLM-FLOOD-002",
        scheme="flood_relief",
        incident_date=date(2026, 6, 15),
        flood_relief=FloodReliefInputs(
            eligible_area=EligibleArea(
                value="1",
                unit="hectare",
            )
        ),
    )

    result = calculate_claim(request)

    assert len(result["notices"]) >= 2
    assert any("synthetic" in notice.lower() for notice in result["notices"])
