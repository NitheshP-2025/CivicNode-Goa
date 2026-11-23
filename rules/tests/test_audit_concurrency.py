
from concurrent.futures import ThreadPoolExecutor

from rules.receipts.audit_chain import (
    append_audit_event,
    verify_audit_chain,
)


def test_concurrent_audit_writes_preserve_chain(tmp_path):
    database_path = tmp_path / "concurrent_audit.db"

    def write_event(index):
        return append_audit_event(
            event_type="TEST_EVENT",
            entity_id=f"CLAIM-{index}",
            payload={"index": index},
            database_path=database_path,
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(write_event, range(30)))

    verification = verify_audit_chain(database_path)

    assert len(results) == 30
    assert verification["valid"] is True
    assert verification["entries_checked"] == 30
