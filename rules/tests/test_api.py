
from dataclasses import replace

from fastapi.testclient import TestClient

from rules.api import app
from rules.config import settings
from rules.security import verify_internal_key


client = TestClient(app)

TEST_KEY = "civicnode-test-key"


def flood_payload():
    return {
        "claim_id": "CLM-FLOOD-001",
        "scheme": "flood_relief",
        "incident_date": "2026-06-15",
        "flood_relief": {
            "eligible_area": {
                "value": "2",
                "unit": "hectare",
            }
        },
    }


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_calculation_succeeds_with_auth_dependency_override():
    app.dependency_overrides[verify_internal_key] = (
        lambda: None
    )

    try:
        # This test checks endpoint availability only.
        response = client.post(
            "/calc",
            json=flood_payload(),
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_missing_key_returns_401(monkeypatch):
    from rules import security

    monkeypatch.setattr(
        security,
        "settings",
        replace(settings, internal_api_key=TEST_KEY),
    )

    response = client.post(
        "/calc",
        json=flood_payload(),
    )

    assert response.status_code == 401


def test_invalid_key_returns_403(monkeypatch):
    from rules import security

    monkeypatch.setattr(
        security,
        "settings",
        replace(settings, internal_api_key=TEST_KEY),
    )

    response = client.post(
        "/calc",
        json=flood_payload(),
        headers={"X-Internal-Key": "wrong-key"},
    )

    assert response.status_code == 403


def test_evaluate_rules_endpoint():
    app.dependency_overrides[verify_internal_key] = (
        lambda: None
    )

    payload = {
        "claim_id": "CLM-EVAL-001",
        "scheme": "flood_relief",
        "incident_date": "2026-06-15",
        "facts": {
            "documents_verified": True,
            "registry_match": True,
            "duplicate_status": "clear",
            "flood_evidence": {
                "status": "flooded",
                "overlap_percent": "80",
            },
            "eligible_area": {
                "value": "2",
                "unit": "hectare",
            },
        },
    }

    try:
        response = client.post(
            "/rules/evaluate",
            json=payload,
        )

        assert response.status_code == 200, response.text

        result = response.json()

        assert result["claim_id"] == "CLM-EVAL-001"
        assert result["scheme"] == "flood_relief"

    finally:
        app.dependency_overrides.clear()


def test_evaluate_rules_rejects_invalid_request():
    app.dependency_overrides[verify_internal_key] = (
        lambda: None
    )

    try:
        response = client.post(
            "/rules/evaluate",
            json={
                "claim_id": "INVALID",
                "scheme": "unknown_scheme",
                "incident_date": "2026-06-15",
                "facts": {},
            },
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()
