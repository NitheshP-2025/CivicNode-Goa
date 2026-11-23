
import sqlite3

from rules.receipts.audit_chain import (
    append_audit_event,
    verify_audit_chain,
)


def create_test_chain(database_path):
    for index in range(1, 4):
        append_audit_event(
            event_type="TEST_EVENT",
            entity_id=f"CLAIM-{index}",
            payload={"index": index},
            database_path=database_path,
        )


def test_modified_audit_payload_is_detected(tmp_path):
    database_path = tmp_path / "tampered.db"
    create_test_chain(database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE audit_entries
            SET payload_json = ?
            WHERE id = 2
            """,
            ('{"index":999}',),
        )

    result = verify_audit_chain(database_path)

    assert result["valid"] is False
    assert "Entry hash mismatch" in result["error"]


def test_deleted_middle_audit_entry_is_detected(tmp_path):
    database_path = tmp_path / "deleted.db"
    create_test_chain(database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "DELETE FROM audit_entries WHERE id = 2"
        )

    result = verify_audit_chain(database_path)

    assert result["valid"] is False
    assert "Previous hash mismatch" in result["error"]
