
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal
from pydantic import model_validator

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
)


# All request models reject unexpected fields.
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Accept decimal values only as JSON strings.
# This avoids losing precision through floating-point numbers.
def validate_decimal_string(value: object) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("Decimal values must be provided as strings")

    try:
        result = Decimal(value)
    except InvalidOperation:
        raise ValueError("Invalid decimal value")

    if not result.is_finite():
        raise ValueError("Decimal value must be finite")

    return result


DecimalString = Annotated[
    Decimal,
    BeforeValidator(validate_decimal_string),
]


# Land area and its measurement unit.
class EligibleArea(StrictModel):
    value: Annotated[DecimalString, Field(gt=0)]
    unit: Literal["hectare", "are", "sq_m"]


# Satellite-derived flood evidence.
class FloodEvidence(StrictModel):
    status: Literal["flooded", "not_flooded", "uncertain"]
    overlap_percent: Annotated[
        DecimalString,
        Field(ge=0, le=100),
    ] | None = None


# Facts supplied by the main backend.
# Unknown information must remain None, not be guessed.
class ClaimFacts(StrictModel):
    survey_number: str | None = None
    eligible_area: EligibleArea | None = None
    registry_match: bool | None = None

    flood_evidence: FloodEvidence | None = None

    duplicate_status: Literal[
        "clear",
        "possible_duplicate",
        "confirmed_duplicate",
    ] | None = None

    documents_verified: bool | None = None


# Request received by POST /rules/evaluate.
class EvaluateRequest(StrictModel):
    claim_id: Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"),
    ]

    scheme: Literal["flood_relief", "land_acquisition"]
    incident_date: date
    rule_version: str | None = None
    facts: ClaimFacts



# Inputs for flood relief calculations.
class FloodReliefInputs(StrictModel):
    eligible_area: EligibleArea


# Individual structure valuation.
class StructureInput(StrictModel):
    description: str
    value: Annotated[DecimalString, Field(ge=0)]


# Individual tree valuation.
class TreeInput(StrictModel):
    description: str
    value: Annotated[DecimalString, Field(ge=0)]


# Inputs for land acquisition calculations.
class LandAcquisitionInputs(StrictModel):
    land_value: Annotated[DecimalString, Field(ge=0)]

    structures: list[StructureInput] = Field(
        default_factory=list
    )

    trees: list[TreeInput] = Field(
        default_factory=list
    )

    interest_start_date: date
    interest_end_date: date


# Request received by POST /calc.
class CalculationRequest(StrictModel):
    claim_id: Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"),
    ]

    scheme: Literal["flood_relief", "land_acquisition"]
    incident_date: date
    rule_version: str | None = None

    flood_relief: FloodReliefInputs | None = None
    land_acquisition: LandAcquisitionInputs | None = None

    @model_validator(mode="after")
    def validate_scheme_inputs(self):
        if self.scheme == "flood_relief":
            if self.flood_relief is None:
                raise ValueError(
                    "Flood relief inputs are required."
                )

            if self.land_acquisition is not None:
                raise ValueError(
                    "Land acquisition inputs are not allowed "
                    "for flood relief."
                )

        elif self.scheme == "land_acquisition":
            if self.land_acquisition is None:
                raise ValueError(
                    "Land acquisition inputs are required."
                )

            if self.flood_relief is not None:
                raise ValueError(
                    "Flood relief inputs are not allowed "
                    "for land acquisition."
                )

        return self
