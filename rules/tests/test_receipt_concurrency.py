
from concurrent.futures import ThreadPoolExecutor

from rules.receipts.storage import (
    save_receipt_with_audit,
    get_receipts_by_claim,
)
from rules.receipts.audit_chain import verify_audit_chain


def test_concurrent_receipt_creation_preserves_audit_chain(tmp_path):
    database_path = tmp_path / "concurrent_receipts.db"

    def create_receipt(index):
        receipt = {
            "receipt_id": f"RCP-TEST-{index:04d}",
            "claim_id": f"CLAIM-{index:04d}",
            "created_at": "2026-11-23T12:00:00+00:00",
            "scheme": "flood_relief",
            "rule_pack": {
                "version": "v1",
            },
        }

        return save_receipt_with_audit(
            receipt,
            database_path=database_path,
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(create_receipt, range(30)))

    verification = verify_audit_chain(database_path)

    assert len(results) == 30
    assert verification["valid"] is True
    assert verification["entries_checked"] == 30

    for index in range(30):
        receipts = get_receipts_by_claim(
            f"CLAIM-{index:04d}",
            database_path=database_path,
        )
        assert len(receipts) == 1
