from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError

from backend.db import json_dump, managed_connection
from backend.service import get_claim, update_pipeline_state

log = logging.getLogger(__name__)


def _failures(stage: str, exc: Exception, pipeline: dict[str, Any]) -> str:
    log.exception("Claim pipeline stage %s failed", stage)
    pipeline["stages"][stage] = {
        "status": "failed",
        "error": f"{stage} failed; officer review is required.",
    }
    return f"{stage}_failed"


def _documents(claim_id: str, path: str | Path | None) -> list[dict[str, Any]]:
    with managed_connection(path) as connection:
        rows = connection.execute(
            "SELECT id, filename, content_type, content FROM documents WHERE claim_id = ? ORDER BY created_at",
            (claim_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _extract_documents(documents: list[dict[str, Any]]):
    from Goa_AI.documents.extract import extract_document
    from Goa_AI.schemas import ExtractionResult

    extracted = [
        extract_document(bytes(doc["content"]), doc["filename"], doc["id"])
        for doc in documents
    ]
    fields_by_name = {}
    for result in extracted:
        for item in result.fields:
            if item.value is None:
                continue
            current = fields_by_name.get(item.name)
            if current is None or item.confidence > current.confidence:
                fields_by_name[item.name] = item
    quality = next((item.quality for item in extracted if not item.quality.ok), extracted[0].quality)
    notes = sorted({note for item in extracted for note in item.notes})
    return ExtractionResult(
        document_id=documents[0]["id"],
        quality=quality,
        is_land_record=all(item.is_land_record for item in extracted),
        fields=list(fields_by_name.values()),
        notes=notes,
    )


def _field_value(extraction: Any, name: str) -> Any:
    return next((field.value for field in extraction.fields if field.name == name), None)


def _registry_match(claim: dict[str, Any], extraction: Any, path: str | Path | None):
    from Goa_AI.documents.validate import normalize_place, normalize_survey
    from Goa_AI.matching.registry_compare import compare_with_registry

    survey = _field_value(extraction, "survey") or claim.get("survey_number")
    village = _field_value(extraction, "village") or claim.get("village")
    taluka = _field_value(extraction, "taluka") or claim.get("taluka")
    with managed_connection(path) as connection:
        records = connection.execute("SELECT * FROM registry ORDER BY registry_id").fetchall()
    registry = None
    for row in records:
        if not survey or normalize_survey(row["survey_number"]) != normalize_survey(str(survey)):
            continue
        if taluka and normalize_place(row["taluka"]) != normalize_place(str(taluka)):
            continue
        if village and normalize_place(row["village"]) != normalize_place(str(village)):
            continue
        registry = dict(row)
        registry["survey"] = registry.pop("survey_number")
        registry["area_ha"] = float(registry["area_ha"])
        registry.pop("registry_id")
        registry.pop("polygon_json")
        break
    if registry is None:
        return survey, village, taluka, None, []
    matches = compare_with_registry(extraction, registry)
    return survey, village, taluka, registry, matches


def _find_duplicate(
    claim: dict[str, Any],
    survey: str | None,
    taluka: str | None,
    path: str | Path | None,
) -> dict[str, Any]:
    from Goa_AI.documents.validate import normalize_place, normalize_survey

    if not survey:
        return {"found": False, "claim_id": None}
    with managed_connection(path) as connection:
        rows = connection.execute(
            """
            SELECT id, tracking_number, survey_number, taluka, mobile, incident_date, status
            FROM claims
            WHERE id != ? AND status != 'draft'
              AND incident_date = ?
            ORDER BY created_at
            """,
            (claim["id"], claim["incident_date"]),
        ).fetchall()
    for row in rows:
        same_plot = (
            row["survey_number"]
            and normalize_survey(row["survey_number"]) == normalize_survey(survey)
            and (
                not taluka
                or not row["taluka"]
                or normalize_place(row["taluka"]) == normalize_place(taluka)
            )
        )
        same_person = row["mobile"] == claim["mobile"]
        if same_plot or same_person:
            return {
                "found": True,
                "claim_id": row["tracking_number"],
                "match_type": "same_plot" if same_plot else "same_farmer",
                "status": row["status"],
            }
    return {"found": False, "claim_id": None}


def _flood_check(claim: dict[str, Any]):
    from Goa_AI.schemas import FloodResult as AIFloodResult
    from flood.query import FloodChecker

    plot = claim.get("plot")
    if plot is None:
        return AIFloodResult(indicated=None, confidence="UNAVAILABLE"), {
            "verdict": "INCONCLUSIVE",
            "reason": "Plot location was not supplied.",
        }
    result = FloodChecker().was_plot_flooded(plot, claim["incident_date"])
    details = result.to_dict()
    if details["verdict"] == "PERMANENTLY_WET" or details["flooded"] is None:
        return AIFloodResult(
            indicated=None,
            confidence="UNAVAILABLE",
            image_date=details.get("observation_date"),
        ), details
    score = details["confidence"]
    confidence = "HIGH" if score >= 0.7 else "MEDIUM" if score >= 0.4 else "LOW"
    return AIFloodResult(
        indicated=details["flooded"],
        confidence=confidence,
        image_date=details.get("observation_date"),
    ), details


def _evaluate_rules(
    claim: dict[str, Any],
    survey: str | None,
    registry: dict[str, Any] | None,
    matches: list[Any],
    duplicate: dict[str, Any],
    flood: Any,
    extraction: Any,
) -> dict[str, Any]:
    from rules.engine.evaluate import evaluate_claim
    from rules.schemas import ClaimFacts, EligibleArea, EvaluateRequest, FloodEvidence

    owner_match = next((item for item in matches if item.field == "owner"), None)
    survey_match = next((item for item in matches if item.field == "survey"), None)
    registry_match = bool(
        owner_match and owner_match.status == "match"
        and survey_match and survey_match.status == "match"
    )
    area = registry.get("area_ha") if registry else None
    if area is None:
        area = _field_value(extraction, "area_ha")
    eligible_area = EligibleArea(value=str(area), unit="hectare") if area is not None else None
    flood_evidence = None
    if claim["scheme"] == "flood_relief":
        if flood.indicated is None:
            flood_evidence = FloodEvidence(status="uncertain")
        else:
            flood_evidence = FloodEvidence(
                status="flooded" if flood.indicated else "not_flooded",
                overlap_percent="0" if not flood.indicated else None,
            )
    facts = ClaimFacts(
        survey_number=survey,
        eligible_area=eligible_area,
        registry_match=registry_match if registry else None,
        flood_evidence=flood_evidence,
        duplicate_status="possible_duplicate" if duplicate["found"] else (
            "clear" if registry else None
        ),
        documents_verified=(
            extraction.quality.ok
            and extraction.is_land_record
            and _field_value(extraction, "owner") is not None
            and survey is not None
        ),
    )
    request = EvaluateRequest(
        claim_id=claim["id"],
        scheme=claim["scheme"],
        incident_date=claim["incident_date"],
        facts=facts,
    )
    return evaluate_claim(request)


def _calculate(claim: dict[str, Any], registry: dict[str, Any] | None, extraction: Any):
    from rules.schemas import CalculationRequest
    from rules.service import calculate_claim

    if claim["scheme"] == "flood_relief":
        area = registry.get("area_ha") if registry else None
        if area is None:
            area = _field_value(extraction, "area_ha")
        if area is None:
            raise ValueError("No land area is available for the calculator.")
        payload = {
            "claim_id": claim["id"],
            "scheme": "flood_relief",
            "incident_date": claim["incident_date"],
            "flood_relief": {
                "eligible_area": {"value": str(area), "unit": "hectare"},
            },
        }
    else:
        inputs = claim.get("land_acquisition")
        if not inputs:
            raise ValueError("Land acquisition inputs are missing.")
        payload = {
            "claim_id": claim["id"],
            "scheme": "land_acquisition",
            "incident_date": claim["incident_date"],
            "land_acquisition": inputs,
        }
    return calculate_claim(CalculationRequest.model_validate(payload))


def _persist(
    claim_id: str,
    path: str | Path | None,
    pipeline: dict[str, Any],
    status: str = "processing",
    lane: str | None = None,
    flags: list[str] | None = None,
    amount: str | None = None,
    survey: str | None = None,
    village: str | None = None,
    taluka: str | None = None,
) -> None:
    update_pipeline_state(
        claim_id, status, lane, pipeline, flags, amount,
        survey, village, taluka, path,
    )


def run_pipeline(claim_id: str, path: str | Path | None = None) -> dict[str, Any]:
    claim = get_claim(claim_id, path)
    pipeline: dict[str, Any] = {"status": "running", "stages": {}}
    errors: list[str] = []
    extraction = None
    survey = claim.get("survey_number")
    village = claim.get("village")
    taluka = claim.get("taluka")
    registry = None
    matches = []
    duplicate = {"found": False, "claim_id": None}
    from Goa_AI.schemas import (
        CalcSummary, ClaimBundle, DuplicateResult, ExtractionResult, FloodResult,
        QualityReport, RuleResult,
    )

    extraction = ExtractionResult(
        document_id=claim_id,
        quality=QualityReport(
            ok=False, blur_score=0, width=0, height=0, brightness=0,
            code="EXTRACTION_FAILED", message="Document extraction is unavailable.",
        ),
        fields=[],
        notes=[],
    )
    flood = FloodResult(indicated=None, confidence="UNAVAILABLE")
    rule = RuleResult(status="needs_review")
    calculation = None

    def run_stage(name: str, action: Callable[[], Any], fallback: Any) -> Any:
        nonlocal errors
        pipeline["current_stage"] = name
        _persist(claim_id, path, pipeline)
        try:
            result = action()
            pipeline["stages"][name] = {"status": "complete"}
            return result
        except Exception as exc:
            errors.append(_failures(name, exc, pipeline))
            return fallback
        finally:
            pipeline["current_stage"] = None
            _persist(claim_id, path, pipeline)

    docs = run_stage(
        "document_extraction",
        lambda: _extract_documents(_documents(claim_id, path)),
        extraction,
    )
    extraction = docs
    if "llm_unavailable" in extraction.notes or not os.getenv("XAI_API_KEY"):
        errors.append("grok_vision_unavailable")
        pipeline["stages"]["document_extraction"]["grok"] = "unavailable"
    else:
        pipeline["stages"]["document_extraction"]["grok"] = "used"
    if "ocr_unavailable" in extraction.notes:
        errors.append("ocr_unavailable")

    def registry_stage():
        nonlocal survey, village, taluka, registry, matches
        survey, village, taluka, registry, matches = _registry_match(claim, extraction, path)
        if registry is None:
            errors.append("registry_record_not_found")
            pipeline["stages"]["registry_match"] = {
                "status": "needs_review",
                "reason": "No mock registry record matched this survey and taluka.",
            }
        return registry

    run_stage("registry_match", registry_stage, None)

    def duplicate_stage():
        nonlocal duplicate
        duplicate = _find_duplicate(claim, survey, taluka, path)
        return duplicate

    run_stage("duplicate_check", duplicate_stage, duplicate)

    flood, flood_details = run_stage(
        "flood_check",
        lambda: _flood_check(claim),
        (FloodResult(indicated=None, confidence="UNAVAILABLE"), {
            "verdict": "UNAVAILABLE", "reason": "Flood check failed.",
        }),
    )

    rule_payload = run_stage(
        "rules_evaluation",
        lambda: _evaluate_rules(claim, survey, registry, matches, duplicate, flood, extraction),
        None,
    )
    if rule_payload is not None:
        rule = RuleResult(
            status="eligible" if rule_payload["overall_status"] == "passed" else "needs_review",
            rule_id=rule_payload.get("rule_pack", {}).get("version"),
            clause=None,
        )

    calc_payload = run_stage(
        "calculation",
        lambda: _calculate(claim, registry, extraction),
        None,
    )
    amount = None
    if calc_payload:
        calculation_result = calc_payload["calculation"]
        amount = calculation_result.get("total")
        calculation = CalcSummary(
            total=amount,
            formula=calculation_result.get("formula"),
        )

    matches_for_recommendation = matches
    if registry is None and not matches_for_recommendation:
        matches_for_recommendation = []
    bundle = ClaimBundle(
        extraction=extraction,
        matches=matches_for_recommendation,
        rule=rule,
        flood=flood,
        duplicate=DuplicateResult(
            found=duplicate["found"], claim_id=duplicate.get("claim_id"),
        ),
        calculation=calculation,
        service_errors=sorted(set(errors)),
    )
    recommendation = run_stage(
        "recommendation",
        lambda: _recommend(bundle),
        {
            "lane": "AMBER",
            "summary": "Automated recommendation is unavailable; officer review is required.",
            "flags": ["RECOMMENDATION_FAILED"],
            "reasons": [],
        },
    )

    pipeline.update({
        "status": "complete",
        "current_stage": None,
        "errors": sorted(set(errors)),
        "extraction": extraction.model_dump(mode="json"),
        "registry": registry,
        "matches": [item.model_dump(mode="json") for item in matches],
        "duplicate": duplicate,
        "flood": flood_details,
        "rules": rule_payload,
        "calculation": calc_payload,
        "recommendation": recommendation,
        "notices": [
            "AI screening is advisory; the authorised officer makes the decision.",
            "Satellite data indicates water coverage only; damage must be confirmed by an officer.",
            "Synthetic rule and registry data are for demonstration only.",
        ],
    })
    lane = recommendation["lane"]
    final_status = "ready_for_officer" if lane == "GREEN" else "needs_review"
    pipeline["status"] = final_status
    _persist(
        claim_id, path, pipeline, final_status, lane,
        recommendation.get("flags", []), amount, survey, village, taluka,
    )
    return get_claim(claim_id, path)


def _recommend(bundle: Any) -> dict[str, Any]:
    from Goa_AI.recommend.engine import recommend

    return recommend(bundle).model_dump(mode="json")

