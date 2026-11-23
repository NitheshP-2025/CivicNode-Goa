
from fastapi.testclient import TestClient

from rules.api import app
from rules.security import verify_internal_key
from rules.receipts import audit_chain


client = TestClient(app)


def test_audit_verification_endpoint_returns_valid(monkeypatch, tmp_path):
    from dataclasses import replace

    test_settings = replace(
        audit_chain.settings,
        database_path=tmp_path / "audit.db",
    )

    monkeypatch.setattr(audit_chain, "settings", test_settings)
    app.dependency_overrides[verify_internal_key] = lambda: None

    try:
        response = client.get("/audit/verify")

        assert response.status_code == 200
        assert response.json()["valid"] is True
        assert response.json()["entries_checked"] == 0
        assert response.json()["audit_integrity"] == "valid"
    finally:
        app.dependency_overrides.clear()



def test_audit_verification_requires_authentication():
    response = client.get("/audit/verify")

    assert response.status_code in (401, 503)
