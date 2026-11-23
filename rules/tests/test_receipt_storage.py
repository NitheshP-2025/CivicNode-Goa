
import pytest

from rules.receipts.storage import (
    save_receipt,
    get_receipt,
    get_receipts_by_claim,
)


@pytest.fixture
def sample_receipt():
    return {
        "receipt_id": "RCP-TEST123",
        "claim_id": "CLM-001",
        "created_at": "2026-11-23T10:00:00Z",
        "scheme": "flood_relief",
        "calculation": {
            "total": "2222.22",
            "currency": "INR",
        },
    }


def test_save_and_retrieve_receipt(tmp_path, sample_receipt):
    db = tmp_path / "receipts.db"

    save_receipt(sample_receipt, db)

    stored = get_receipt("RCP-TEST123", db)

    assert stored == sample_receipt


def test_unknown_receipt_returns_none(tmp_path):
    db = tmp_path / "receipts.db"

    result = get_receipt("RCP-UNKNOWN", db)

    assert result is None


def test_receipts_can_be_retrieved_by_claim(
    tmp_path,
    sample_receipt,
):
    db = tmp_path / "receipts.db"

    save_receipt(sample_receipt, db)

    results = get_receipts_by_claim("CLM-001", db)

    assert len(results) == 1
    assert results[0]["receipt_id"] == "RCP-TEST123"


def test_duplicate_receipt_id_is_rejected(
    tmp_path,
    sample_receipt,
):
    db = tmp_path / "receipts.db"

    save_receipt(sample_receipt, db)

    with pytest.raises(Exception):
        save_receipt(sample_receipt, db)


def test_missing_receipt_fields_are_rejected(tmp_path):
    db = tmp_path / "receipts.db"

    with pytest.raises(ValueError):
        save_receipt(
            {"claim_id": "CLM-001"},
            db,
        )
