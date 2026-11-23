
from dataclasses import replace

from fastapi.testclient import TestClient

from rules.api import app
from rules.security import verify_internal_key
from rules.receipts import storage, audit_chain
from rules.api import app
from rules.receipts import storage, audit_chain

client = TestClient(app)


def test_retrieve_saved_receipt(monkeypatch, tmp_path):
    test_settings = replace(
        storage.settings,
        database_path=tmp_path / "receipts.db",
    )

    audit_settings = replace(
        audit_chain.settings,
        database_path=tmp_path / "receipts.db",
    )

    monkeypatch.setattr(storage, "settings", test_settings)
    monkeypatch.setattr(audit_chain, "settings", audit_settings)

    storage.save_receipt(
        {
            "receipt_id": "RCP-TEST123",
            "claim_id": "CLM-001",
            "created_at": "2026-11-23T10:00:00Z",
            "scheme": "flood_relief",
            "rule_pack": {"version": "v1"},
            "calculation": {"total": "2222.22"},
        }
    )

    app.dependency_overrides[verify_internal_key] = lambda: None

    try:
        response = client.get("/receipts/RCP-TEST123")

        assert response.status_code == 200
        assert response.json()["receipt_id"] == "RCP-TEST123"
        assert response.json()["claim_id"] == "CLM-001"
    finally:
        app.dependency_overrides.clear()


def test_unknown_receipt_returns_404(monkeypatch, tmp_path):
    test_settings = replace(
        storage.settings,
        database_path=tmp_path / "receipts.db",
    )

    monkeypatch.setattr(storage, "settings", test_settings)

    app.dependency_overrides[verify_internal_key] = lambda: None

    try:
        response = client.get("/receipts/RCP-UNKNOWN")

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_complete_receipt_workflow(monkeypatch, tmp_path):
    from dataclasses import replace

    test_db = tmp_path / "workflow.db"

    monkeypatch.setattr(
        storage,
        "settings",
        replace(storage.settings, database_path=test_db),
    )

    monkeypatch.setattr(
        audit_chain,
        "settings",
        replace(audit_chain.settings, database_path=test_db),
    )

    app.dependency_overrides[verify_internal_key] = lambda: None

    payload = {
        "claim_id": "CLM-WORKFLOW-001",
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
        response = client.post("/receipts/pdf", json=payload)

        print("STATUS:", response.status_code)
        print("ERROR:", response.text)

        assert response.status_code == 200
        
        assert response.content.startswith(b"%PDF")

        saved_receipts = storage.get_receipts_by_claim(
            "CLM-WORKFLOW-001"
        )

        assert len(saved_receipts) == 1

        receipt = saved_receipts[0]

        assert receipt["scheme"] == "flood_relief"
        assert receipt["calculation"]["total"] == "2222.22"

        audit_result = audit_chain.verify_audit_chain()

        assert audit_result["valid"] is True
        assert audit_result["entries_checked"] == 1

    finally:
        app.dependency_overrides.clear()
