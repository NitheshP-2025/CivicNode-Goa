
from fastapi.testclient import TestClient

from rules.api import app
from rules.security import verify_internal_key


client = TestClient(app)


def test_receipt_pdf_endpoint_returns_downloadable_pdf():
    app.dependency_overrides[verify_internal_key] = lambda: None

    payload = {
        "claim_id": "CLM-PDF-001",
        "scheme": "flood_relief",
        "incident_date": "2026-06-15",
        "rule_pack": {
            "version": "v1",
            "status": "demo",
            "sha256": "a" * 64,
        },
        "calculation": {
            "formula": "eligible_area_hectares * rate_per_hectare",
            "total": "2222.22",
            "currency": "INR",
            "rounding": "ROUND_HALF_UP",
        },
        "notices": ["Synthetic demonstration calculation."],
    }

    try:
        response = client.post(
            "/receipts/pdf",
            json=payload,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")
        assert "attachment" in response.headers["content-disposition"]

    finally:
        app.dependency_overrides.clear()


def test_receipt_pdf_endpoint_rejects_invalid_payload():
    app.dependency_overrides[verify_internal_key] = lambda: None

    try:
        response = client.post(
            "/receipts/pdf",
            json={},
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()
