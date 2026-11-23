
import json
import sqlite3

from pathlib import Path
from typing import Any
from contextlib import contextmanager

from rules.config import settings
from rules.receipts.audit_chain import (
    initialize_audit_database,
    append_audit_event_in_transaction,
)


def _connect(database_path=None):
    path = Path(database_path or settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def _managed_connection(database_path=None):
    connection = _connect(database_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()

def initialize_receipt_storage(database_path=None):
    with _managed_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                receipt_json TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_receipts_claim_id
            ON receipts(claim_id)
            """
        )


def save_receipt(
    
    receipt: dict[str, Any],
    database_path=None,
) -> dict:
    required_fields = [
        "receipt_id",
        "claim_id",
        "created_at",
    ]

    missing = [
        field for field in required_fields
        if field not in receipt
    ]
    if not isinstance(receipt, dict):
            raise ValueError("Receipt must be a dictionary")
    
    if missing:
        raise ValueError(
            f"Receipt is missing required fields: {missing}"
        )

    

    receipt_json = json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    initialize_receipt_storage(database_path)

    with _managed_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO receipts (
                receipt_id,
                claim_id,
                created_at,
                receipt_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                receipt["receipt_id"],
                receipt["claim_id"],
                receipt["created_at"],
                receipt_json,
            ),
        )

    return receipt


def get_receipt(
    receipt_id: str,
    database_path=None,
) -> dict | None:
    initialize_receipt_storage(database_path)

    with _managed_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT receipt_json
            FROM receipts
            WHERE receipt_id = ?
            """,
            (receipt_id,),
        ).fetchone()

    if row is None:
        return None

    return json.loads(row["receipt_json"])


def get_receipts_by_claim(
    claim_id: str,
    database_path=None,
) -> list[dict]:
    initialize_receipt_storage(database_path)

    with _managed_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT receipt_json
            FROM receipts
            WHERE claim_id = ?
            ORDER BY created_at DESC
            """,
            (claim_id,),
        ).fetchall()

    return [
        json.loads(row["receipt_json"])
        for row in rows
    ]


def save_receipt_with_audit(
    receipt: dict[str, Any],
    database_path=None,
) -> dict:
    """
    Store a receipt and its audit event atomically.
    Both succeed or both roll back.
    """

    if not isinstance(receipt, dict):
        raise ValueError("Receipt must be a dictionary")

    required_fields = [
        "receipt_id",
        "claim_id",
        "created_at",
        "scheme",
        "rule_pack",
    ]

    missing = [
        field for field in required_fields
        if field not in receipt
    ]

    if missing:
        raise ValueError(
            f"Receipt is missing required fields: {missing}"
        )

    receipt_json = json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    initialize_receipt_storage(database_path)
    initialize_audit_database(database_path)

    with _managed_connection(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")

        connection.execute(
            """
            INSERT INTO receipts (
                receipt_id,
                claim_id,
                created_at,
                receipt_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                receipt["receipt_id"],
                receipt["claim_id"],
                receipt["created_at"],
                receipt_json,
            ),
        )

        append_audit_event_in_transaction(
            connection=connection,
            event_type="RECEIPT_CREATED",
            entity_id=receipt["claim_id"],
            payload={
                "receipt_id": receipt["receipt_id"],
                "scheme": receipt["scheme"],
                "rule_pack_version": receipt["rule_pack"]["version"],
            },
        )

    return receipt
