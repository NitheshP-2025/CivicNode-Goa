
from dataclasses import replace

from fastapi.testclient import TestClient

from rules.api import app
from rules.security import verify_internal_key
from rules.receipts import storage


client = TestClient(app)


def test_download_saved_receipt_pdf(monkeypatch, tmp_path):
    test_settings = replace(
        storage.settings,
        database_path=tmp_path / "receipts.db",
    )

    monkeypatch.setattr(storage, "settings", test_settings)

    receipt = {
        "receipt_id": "RCP-DOWNLOAD123",
        "claim_id": "CLM-DOWNLOAD-001",
        "created_at": "2026-11-23T10:00:00Z",
        "generated_at": "2026-11-23T10:00:00Z",
        "scheme": "flood_relief",
        "incident_date": "2026-06-15",
        "rule_pack": {
            "version": "v1",
            "status": "demo",
            "sha256": "a" * 64,
        },
        "calculation": {
            "formula": "area * rate",
            "total": "2222.22",
            "currency": "INR",
            "rounding": "ROUND_HALF_UP",
        },
        "notices": ["Demonstration receipt."],
    }

    storage.save_receipt(receipt)

    app.dependency_overrides[verify_internal_key] = lambda: None

    try:
        response = client.get(
            "/receipts/RCP-DOWNLOAD123/pdf"
        )

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")
        assert response.headers["content-type"] == "application/pdf"
        assert "RCP-DOWNLOAD123.pdf" in response.headers[
            "content-disposition"
        ]

    finally:
        app.dependency_overrides.clear()


def test_download_unknown_receipt_returns_404(monkeypatch, tmp_path):
    test_settings = replace(
        storage.settings,
        database_path=tmp_path / "receipts.db",
    )

    monkeypatch.setattr(storage, "settings", test_settings)

    app.dependency_overrides[verify_internal_key] = lambda: None

    try:
        response = client.get(
            "/receipts/RCP-UNKNOWN/pdf"
        )

        assert response.status_code == 404

    finally:
        app.dependency_overrides.clear()
