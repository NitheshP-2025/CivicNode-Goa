
import sqlite3

from rules.receipts.audit_chain import (
    append_audit_event,
    verify_audit_chain,
)


def test_empty_audit_chain_is_valid(tmp_path):
    db = tmp_path / "audit.db"

    result = verify_audit_chain(db)

    assert result["valid"] is True
    assert result["entries_checked"] == 0


def test_append_creates_audit_entry(tmp_path):
    db = tmp_path / "audit.db"

    entry = append_audit_event(
        event_type="CLAIM_CALCULATED",
        entity_id="CLM-001",
        payload={"total": "2222.22"},
        database_path=db,
    )

    assert entry["id"] == 1
    assert len(entry["entry_hash"]) == 64


def test_second_entry_links_to_first(tmp_path):
    db = tmp_path / "audit.db"

    first = append_audit_event(
        "CLAIM_CREATED",
        "CLM-001",
        {"status": "submitted"},
        db,
    )

    second = append_audit_event(
        "CLAIM_CALCULATED",
        "CLM-001",
        {"total": "2222.22"},
        db,
    )

    assert second["previous_hash"] == first["entry_hash"]


def test_valid_chain_passes_verification(tmp_path):
    db = tmp_path / "audit.db"

    append_audit_event("CLAIM_CREATED", "CLM-001", {"status": "submitted"}, db)
    append_audit_event("CLAIM_CALCULATED", "CLM-001", {"total": "2222.22"}, db)

    result = verify_audit_chain(db)

    assert result["valid"] is True
    assert result["entries_checked"] == 2


def test_modified_entry_is_detected(tmp_path):
    db = tmp_path / "audit.db"

    append_audit_event(
        "CLAIM_CREATED",
        "CLM-001",
        {"status": "submitted"},
        db,
    )

    with sqlite3.connect(db) as connection:
        connection.execute(
            """
            UPDATE audit_entries
            SET payload_json = ?
            WHERE id = 1
            """,
            ('{"status":"approved"}',),
        )

    result = verify_audit_chain(db)

    assert result["valid"] is False
    assert "Entry hash mismatch" in result["error"]


def test_modified_previous_hash_is_detected(tmp_path):
    db = tmp_path / "audit.db"

    append_audit_event("CLAIM_CREATED", "CLM-001", {"status": "submitted"}, db)
    append_audit_event("CLAIM_CALCULATED", "CLM-001", {"total": "2222.22"}, db)

    with sqlite3.connect(db) as connection:
        connection.execute(
            """
            UPDATE audit_entries
            SET previous_hash = ?
            WHERE id = 2
            """,
            ("f" * 64,),
        )

    result = verify_audit_chain(db)

    assert result["valid"] is False
    assert "Previous hash mismatch" in result["error"]


def test_empty_event_type_is_rejected(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        append_audit_event("", "CLM-001", {}, tmp_path / "audit.db")


def test_non_dictionary_payload_is_rejected(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        append_audit_event(
            "CLAIM_CREATED",
            "CLM-001",
            "invalid payload",
            tmp_path / "audit.db",
        )
