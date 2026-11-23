from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Plot(StrictModel):
    plot_id: str | None = None
    polygon: list[tuple[float, float]] | None = None
    lat: Annotated[float, Field(ge=-90, le=90)] | None = None
    lon: Annotated[float, Field(ge=-180, le=180)] | None = None
    area_sq_m: Annotated[float, Field(gt=0)] | None = None

    @model_validator(mode="after")
    def validate_coordinates(self) -> "Plot":
        if self.polygon is not None:
            if len(self.polygon) < 3:
                raise ValueError("A plot polygon needs at least three points.")
            if any(not -180 <= lon <= 180 or not -90 <= lat <= 90
                   for lon, lat in self.polygon):
                raise ValueError("Plot coordinates must be longitude/latitude pairs.")
        elif any(value is not None for value in (self.lat, self.lon, self.area_sq_m)):
            if None in (self.lat, self.lon, self.area_sq_m):
                raise ValueError("A point plot requires latitude, longitude and area_sq_m.")
        return self


class LandAcquisitionInput(StrictModel):
    land_value: Annotated[Decimal, Field(ge=0)]
    structures: list[dict[str, str | Decimal]] = Field(default_factory=list)
    trees: list[dict[str, str | Decimal]] = Field(default_factory=list)
    interest_start_date: date
    interest_end_date: date


class ClaimCreate(StrictModel):
    farmer_name: Annotated[str, Field(min_length=1, max_length=120)]
    mobile: Annotated[str, Field(pattern=r"^(?:\+?91)?[6-9]\d{9}$")]
    scheme: Literal["flood_relief", "land_acquisition"]
    incident_date: date
    narrative: Annotated[str, Field(max_length=5000)] = ""
    survey_number: Annotated[str | None, Field(max_length=40)] = None
    village: Annotated[str | None, Field(max_length=100)] = None
    taluka: Annotated[str | None, Field(max_length=100)] = None
    plot: Plot | None = None
    land_acquisition: LandAcquisitionInput | None = None

    @model_validator(mode="after")
    def validate_scheme_fields(self) -> "ClaimCreate":
        if self.scheme == "land_acquisition" and self.land_acquisition is None:
            raise ValueError("Land acquisition inputs are required for this scheme.")
        if self.scheme == "flood_relief" and self.land_acquisition is not None:
            raise ValueError("Land acquisition inputs are not allowed for flood relief.")
        return self


class OtpVerify(StrictModel):
    code: Annotated[str, Field(pattern=r"^\d{6}$")]


class OfficerDecision(StrictModel):
    decision: Literal["approve", "request_information", "field_inspection", "reject"]
    officer_id: Annotated[str, Field(min_length=1, max_length=100)]
    reason: Annotated[str, Field(max_length=1000)] = ""

