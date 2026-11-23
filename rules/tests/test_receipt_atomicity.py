
import pytest

from rules.receipts import storage, audit_chain
from rules.receipts.storage import (
    save_receipt_with_audit,
    get_receipt,
)


@pytest.fixture
def sample_receipt():
    return {
        "receipt_id": "RCP-ATOMIC001",
        "claim_id": "CLM-ATOMIC-001",
        "created_at": "2026-11-23T10:00:00Z",
        "scheme": "flood_relief",
        "rule_pack": {
            "version": "v1",
            "status": "demo",
            "sha256": "a" * 64,
        },
        "calculation": {
            "total": "2222.22",
            "currency": "INR",
        },
    }


def test_receipt_and_audit_are_rolled_back_together(
    monkeypatch,
    tmp_path,
    sample_receipt,
):
    db = tmp_path / "atomicity.db"

    def simulate_audit_failure(*args, **kwargs):
        raise RuntimeError("Simulated audit database failure")

    monkeypatch.setattr(
        storage,
        "append_audit_event_in_transaction",
        simulate_audit_failure,
    )

    with pytest.raises(RuntimeError):
        save_receipt_with_audit(sample_receipt, db)

    # Receipt must not exist after transaction rollback.
    assert get_receipt("RCP-ATOMIC001", db) is None

    # Audit chain must also remain empty.
    result = audit_chain.verify_audit_chain(db)

    assert result["valid"] is True
    assert result["entries_checked"] == 0


def test_successful_atomic_save_creates_both_records(
    tmp_path,
    sample_receipt,
):
    db = tmp_path / "atomic-success.db"

    save_receipt_with_audit(sample_receipt, db)

    stored = get_receipt("RCP-ATOMIC001", db)
    audit_result = audit_chain.verify_audit_chain(db)

    assert stored is not None
    assert stored["claim_id"] == "CLM-ATOMIC-001"
    assert audit_result["valid"] is True
    assert audit_result["entries_checked"] == 1
