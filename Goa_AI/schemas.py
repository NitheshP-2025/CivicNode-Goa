"""Shared data formats. Keep in sync with contracts/*.schema.json."""
from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

Lane = Literal["GREEN", "AMBER", "RED"]
FloodConfidence = Literal["HIGH", "MEDIUM", "LOW", "UNAVAILABLE"]


class FieldResult(BaseModel):
    name: str
    value: Optional[Union[str, float]] = None
    confidence: float = 0.0
    bbox: Optional[List[float]] = None   # [x, y, w, h] as 0-1 fractions of the page
    page: int = 0
    unit_original: Optional[str] = None
    source: Optional[str] = None         # "ocr", "llm" or "ocr+llm"


class QualityReport(BaseModel):
    ok: bool
    blur_score: float
    width: int
    height: int
    brightness: float
    code: Optional[str] = None           # LOW_RESOLUTION, BLURRY, DARK, OVEREXPOSED
    message: Optional[str] = None


class ExtractionResult(BaseModel):
    document_id: str
    quality: QualityReport
    is_land_record: bool = True
    fields: List[FieldResult] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    field: str
    status: Literal["match", "possible", "mismatch", "missing"]
    extracted: Optional[Union[str, float]] = None
    registry: Optional[Union[str, float]] = None
    detail: Optional[str] = None


class CompareRequest(BaseModel):
    extraction: ExtractionResult
    registry: dict   # owner (or owners), survey, area_ha, village, taluka


class RuleResult(BaseModel):
    status: Literal["eligible", "not_eligible", "needs_review"]
    rule_id: Optional[str] = None
    clause: Optional[str] = None


class FloodResult(BaseModel):
    indicated: Optional[bool] = None
    confidence: FloodConfidence = "UNAVAILABLE"
    image_date: Optional[str] = None


class DuplicateResult(BaseModel):
    found: bool = False
    claim_id: Optional[str] = None


class CalcSummary(BaseModel):
    total: Optional[str] = None          # exactly as the calculator returned it
    formula: Optional[str] = None


class ClaimBundle(BaseModel):
    extraction: ExtractionResult
    matches: List[MatchResult] = Field(default_factory=list)
    rule: RuleResult
    flood: FloodResult
    duplicate: DuplicateResult = Field(default_factory=DuplicateResult)
    calculation: Optional[CalcSummary] = None
    service_errors: List[str] = Field(default_factory=list)


class Reason(BaseModel):
    code: str
    text: str


class Recommendation(BaseModel):
    lane: Lane
    reasons: List[Reason]
    summary: str
    flags: List[str] = Field(default_factory=list)
