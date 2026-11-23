
import hashlib
import json
import sqlite3

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rules.config import settings


GENESIS_HASH = "0" * 64


def _get_database_path(database_path=None) -> Path:
    path = Path(database_path or settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect(database_path=None):
    path = _get_database_path(database_path)
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


def _canonical_json(data: dict) -> str:
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _calculate_hash(entry: dict) -> str:
    content = {
        "event_type": entry["event_type"],
        "entity_id": entry["entity_id"],
        "payload_json": entry["payload_json"],
        "created_at": entry["created_at"],
        "previous_hash": entry["previous_hash"],
    }

    encoded = _canonical_json(content).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def initialize_audit_database(database_path=None) -> None:
    with _managed_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL UNIQUE
            )
            """
        )


def append_audit_event_in_transaction(
    connection,
    event_type: str,
    entity_id: str,
    payload: dict[str, Any],
) -> dict:
    """Append an audit event inside an existing transaction."""

    if not event_type or not event_type.strip():
        raise ValueError("event_type cannot be empty")

    if not entity_id or not entity_id.strip():
        raise ValueError("entity_id cannot be empty")

    if not isinstance(payload, dict):
        raise ValueError("payload must be a dictionary")

    payload_json = _canonical_json(payload)
    created_at = datetime.now(timezone.utc).isoformat()

    previous = connection.execute(
        """
        SELECT entry_hash
        FROM audit_entries
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    previous_hash = (
        previous["entry_hash"] if previous else GENESIS_HASH
    )

    entry = {
        "event_type": event_type,
        "entity_id": entity_id,
        "payload_json": payload_json,
        "created_at": created_at,
        "previous_hash": previous_hash,
    }

    entry_hash = _calculate_hash(entry)

    cursor = connection.execute(
        """
        INSERT INTO audit_entries (
            event_type,
            entity_id,
            payload_json,
            created_at,
            previous_hash,
            entry_hash
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            entity_id,
            payload_json,
            created_at,
            previous_hash,
            entry_hash,
        ),
    )

    return {
        **entry,
        "id": cursor.lastrowid,
        "entry_hash": entry_hash,
    }


def append_audit_event(
    event_type: str,
    entity_id: str,
    payload: dict[str, Any],
    database_path=None,
) -> dict:
    initialize_audit_database(database_path)

    with _managed_connection(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")

        return append_audit_event_in_transaction(
            connection,
            event_type,
            entity_id,
            payload,
        )


def verify_audit_chain(database_path=None) -> dict:
    initialize_audit_database(database_path)

    with _managed_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM audit_entries
            ORDER BY id ASC
            """
        ).fetchall()

    previous_hash = GENESIS_HASH

    for index, row in enumerate(rows):
        entry = dict(row)

        if entry["previous_hash"] != previous_hash:
            return {
                "valid": False,
                "entries_checked": index,
                "error": (
                    f"Previous hash mismatch at entry {entry['id']}"
                ),
                "last_hash": previous_hash,
            }

        expected_hash = _calculate_hash(entry)

        if entry["entry_hash"] != expected_hash:
            return {
                "valid": False,
                "entries_checked": index,
                "error": (
                    f"Entry hash mismatch at entry {entry['id']}"
                ),
                "last_hash": previous_hash,
            }

        previous_hash = entry["entry_hash"]

    return {
        "valid": True,
        "entries_checked": len(rows),
        "error": None,
        "last_hash": previous_hash,
    }
