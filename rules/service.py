
from rules.engine.loader import load_rule_pack
from rules.schemas import CalculationRequest
from rules.calculator.flood_relief import calculate_flood_relief
from rules.calculator.land_acquisition import calculate_land_acquisition
from rules.receipts.audit_chain import append_audit_event

DEMO_NOTICE = (
    "This calculation uses a synthetic demonstration rule pack. "
    "It is not an official Government of Goa compensation assessment."
)


def calculate_claim(request: CalculationRequest) -> dict:
    """
    Executes the appropriate deterministic calculator
    using parameters from the selected rule pack.
    """

    pack = load_rule_pack(
        scheme=request.scheme,
        version=request.rule_version,
        incident_date=request.incident_date,
    )

    calculation_config = pack["calculation"]

    if request.scheme == "flood_relief":
        inputs = request.flood_relief

        result = calculate_flood_relief(
            eligible_area=inputs.eligible_area.value,
            area_unit=inputs.eligible_area.unit,
            rate_per_hectare=calculation_config["rate_per_hectare"],
        )

    elif request.scheme == "land_acquisition":
        inputs = request.land_acquisition

        structures = [
            {
                "description": item.description,
                "value": item.value,
            }
            for item in inputs.structures
        ]

        trees = [
            {
                "description": item.description,
                "value": item.value,
            }
            for item in inputs.trees
        ]

        result = calculate_land_acquisition(
            land_value=inputs.land_value,
            structures=structures,
            trees=trees,
            solatium_rate=calculation_config["solatium_rate"],
            interest_rate_annual=calculation_config[
                "interest_rate_annual"
            ],
            interest_start_date=inputs.interest_start_date,
            interest_end_date=inputs.interest_end_date,
            interest_basis_days=calculation_config[
                "interest_basis_days"
            ],
        )

    else:
        raise ValueError(f"Unsupported scheme: {request.scheme}")

    notices = list(result.get("notices", []))

    if pack["status"] == "demo":
        notices.append(DEMO_NOTICE)

    notices.append(
        "This calculation requires authorised officer review."
    )

    response = {
        "claim_id": request.claim_id,
        "scheme": request.scheme,
        "incident_date": request.incident_date,
        "rule_pack": {
            "version": pack["version"],
            "status": pack["status"],
            "sha256": pack["_sha256"],
        },
        "calculation": result,
        "notices": notices,
    }

    append_audit_event(
        event_type="CLAIM_CALCULATED",
        entity_id=request.claim_id,
        payload={
            "scheme": request.scheme,
            "incident_date": str(request.incident_date),
            "rule_pack_version": pack["version"],
            "rule_pack_sha256": pack["_sha256"],
            "calculation_total": result["total"],
            "currency": result.get("currency", "INR"),
        },
    )

    return response
