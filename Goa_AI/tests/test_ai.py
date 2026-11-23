"""Run from the repo root:  python -m pytest ai/tests -q"""
import cv2
import numpy as np
import pytest

from ai.documents.extract import _parse_json, llm_extract
from ai.documents.quality import check_quality
from ai.documents.validate import normalize_survey, parse_area, values_agree
from ai.matching.registry_compare import compare_with_registry
from ai.recommend.engine import recommend
from ai.recommend.summary import numbers_in
from ai.schemas import ClaimBundle, ExtractionResult

REGISTRY = {"owner": "Ramesh P", "survey": "45/2", "area_ha": 1.2, "village": "Ponda", "taluka": "Ponda"}


def make_bundle(**over):
    d = {
        "extraction": {
            "document_id": "d1",
            "quality": {"ok": True, "blur_score": 150.0, "width": 1600, "height": 2200, "brightness": 180.0},
            "is_land_record": True,
            "fields": [{"name": n, "value": v, "confidence": c} for n, v, c in
                       [("owner", "Ramesh P", 0.96), ("survey", "45/2", 0.98), ("area_ha", 1.2, 0.91),
                        ("village", "Ponda", 0.9), ("taluka", "Ponda", 0.9)]],
        },
        "matches": [{"field": "owner", "status": "match"}, {"field": "survey", "status": "match"},
                    {"field": "area_ha", "status": "match"}],
        "rule": {"status": "eligible", "rule_id": "EXAMPLE_RULE_V1", "clause": "example clause"},
        "flood": {"indicated": True, "confidence": "HIGH", "image_date": "2026-07-14"},
        "duplicate": {"found": False},
        "calculation": {"total": "24000.00", "formula": "area x rate"},
        "service_errors": [],
    }
    d.update(over)
    return ClaimBundle.model_validate(d)


def extraction(**field_overrides):
    vals = {"owner": "Ramesh P", "survey": "45/2", "area_ha": 1.2, "village": "Ponda", "taluka": "Ponda"}
    vals.update(field_overrides)
    return ExtractionResult.model_validate({
        "document_id": "d1",
        "quality": {"ok": True, "blur_score": 150.0, "width": 1600, "height": 2200, "brightness": 180.0},
        "fields": [{"name": k, "value": v, "confidence": 0.95} for k, v in vals.items()],
    })


# ---------- helpers ----------
def test_area_parsing():
    assert parse_area("1-20-50") == (pytest.approx(1.205), "H-A-S")
    assert parse_area("1.2 ha")[0] == pytest.approx(1.2)
    assert parse_area("12000 sq m")[0] == pytest.approx(1.2)
    assert parse_area("2.5 acres")[0] == pytest.approx(1.011714, rel=1e-5)
    assert parse_area("not an area") == (None, None)


def test_survey_normalisation():
    assert normalize_survey(" 45 - 2 ") == "45/2"
    assert values_agree("survey", "45-2", "45/2")


def test_name_agreement():
    assert values_agree("owner", "Shri Ramesh Naik", "Ramesh  Naik")
    assert not values_agree("owner", "Ramesh Naik", "Suresh Gaonkar")


# ---------- quality gate ----------
def test_quality_gate_catches_blur():
    rng = np.random.default_rng(0)
    sharp = (rng.integers(0, 2, (1000, 1000)) * 255).astype(np.uint8)
    blurred = cv2.GaussianBlur(sharp, (51, 51), 0)
    assert check_quality(sharp).ok
    q = check_quality(blurred)
    assert not q.ok and q.code == "BLURRY" and q.message


# ---------- registry comparison ----------
def test_compare_all_match():
    res = {m.field: m.status for m in compare_with_registry(extraction(), REGISTRY)}
    assert res == {"owner": "match", "survey": "match", "area_ha": "match", "village": "match", "taluka": "match"}


def test_compare_area_bands():
    possible = {m.field: m.status for m in compare_with_registry(extraction(area_ha=1.3), REGISTRY)}
    mismatch = {m.field: m.status for m in compare_with_registry(extraction(area_ha=1.5), REGISTRY)}
    assert possible["area_ha"] == "possible" and mismatch["area_ha"] == "mismatch"


def test_compare_owner_and_survey_mismatch():
    res = {m.field: m.status for m in compare_with_registry(
        extraction(owner="Suresh Gaonkar", survey="99/1"), REGISTRY)}
    assert res["owner"] == "mismatch" and res["survey"] == "mismatch"


# ---------- lanes ----------
def test_green():
    r = recommend(make_bundle())
    assert r.lane == "GREEN" and r.flags == []
    assert numbers_in(r.summary) <= numbers_in(make_bundle().model_dump_json())


def test_amber_when_flood_unavailable():
    assert recommend(make_bundle(flood={"indicated": None, "confidence": "UNAVAILABLE"})).lane == "AMBER"


def test_amber_when_flood_weak_or_unsure():
    assert recommend(make_bundle(flood={"indicated": True, "confidence": "LOW"})).lane == "AMBER"
    assert recommend(make_bundle(flood={"indicated": False, "confidence": "MEDIUM"})).lane == "AMBER"


def test_red_when_flood_not_indicated_with_high_confidence():
    assert recommend(make_bundle(flood={"indicated": False, "confidence": "HIGH"})).lane == "RED"


def test_red_on_duplicate_and_rule_failure():
    assert recommend(make_bundle(duplicate={"found": True, "claim_id": "GOA-1"})).lane == "RED"
    assert recommend(make_bundle(rule={"status": "not_eligible", "rule_id": "R1", "clause": "c"})).lane == "RED"


def test_red_on_survey_mismatch_but_amber_on_area_mismatch():
    survey_bad = make_bundle(matches=[{"field": "owner", "status": "match"},
                                      {"field": "survey", "status": "mismatch", "detail": "survey numbers differ"}])
    area_bad = make_bundle(matches=[{"field": "owner", "status": "match"}, {"field": "survey", "status": "match"},
                                    {"field": "area_ha", "status": "mismatch", "detail": "Area differs by 25.0%"}])
    assert recommend(survey_bad).lane == "RED"
    assert recommend(area_bad).lane == "AMBER"


def test_amber_on_low_confidence_key_field():
    b = make_bundle()
    b.extraction.fields[2].confidence = 0.5
    r = recommend(b)
    assert r.lane == "AMBER" and "LOW_CONFIDENCE" in r.flags


def test_poor_quality_is_amber_without_field_noise():
    b = make_bundle(
        extraction={"document_id": "d1", "fields": [], "is_land_record": True,
                    "quality": {"ok": False, "blur_score": 5.0, "width": 1600, "height": 2200,
                                "brightness": 120.0, "code": "BLURRY", "message": "The photo is blurry."}},
        matches=[])
    r = recommend(b)
    assert r.lane == "AMBER" and "QUALITY_POOR" in r.flags and "FIELD_MISSING" not in r.flags


def test_service_error_is_never_silent_green():
    assert recommend(make_bundle(service_errors=["flood_check"])).lane == "AMBER"


def test_same_input_same_output():
    assert recommend(make_bundle()).model_dump() == recommend(make_bundle()).model_dump()


def test_summary_never_adds_numbers():
    for flood in ({"indicated": True, "confidence": "HIGH", "image_date": "2026-07-14"},
                  {"indicated": False, "confidence": "HIGH"}, {"indicated": None, "confidence": "UNAVAILABLE"}):
        b = make_bundle(flood=flood)
        assert numbers_in(recommend(b).summary) <= numbers_in(b.model_dump_json())


# ---------- Groq vision call (mocked, no network) ----------
def _fake_groq(monkeypatch, reply, reject_json_mode=False):
    import sys
    import types
    calls = []

    class Msg:
        content = reply

    class Choice:
        message = Msg()

    class Resp:
        choices = [Choice()]

    class Completions:
        def create(self, **kw):
            calls.append(kw)
            if reject_json_mode and "response_format" in kw:
                raise RuntimeError("json mode not supported with images")
            return Resp()

    class Chat:
        completions = Completions()

    class FakeGroq:
        def __init__(self, *a, **k):
            self.chat = Chat()

    mod = types.ModuleType("groq")
    mod.Groq = FakeGroq
    monkeypatch.setitem(sys.modules, "groq", mod)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    return calls


IMG = np.zeros((100, 100, 3), np.uint8)


def test_parse_json_handles_fences_and_think_blocks():
    assert _parse_json('<think>hmm</think>```json\n{"owner": "Ramesh P"}\n```') == {"owner": "Ramesh P"}
    assert _parse_json("no json here") is None


def test_llm_extract_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert llm_extract([IMG]) is None


def test_llm_extract_reads_groq_reply(monkeypatch):
    calls = _fake_groq(monkeypatch, '{"owner": "Ramesh P", "survey": "45/2"}')
    assert llm_extract([IMG]) == {"owner": "Ramesh P", "survey": "45/2"}
    assert calls[0]["messages"][0]["content"][1]["type"] == "image_url"


def test_llm_extract_retries_without_json_mode(monkeypatch):
    calls = _fake_groq(monkeypatch, '{"owner": "Ramesh P"}', reject_json_mode=True)
    assert llm_extract([IMG]) == {"owner": "Ramesh P"}
    assert len(calls) == 2 and "response_format" not in calls[1]
