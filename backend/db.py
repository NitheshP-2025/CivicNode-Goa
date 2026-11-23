from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


DEFAULT_DATABASE = Path(__file__).parent / "data" / "civicnode.sqlite3"


def database_path(path: str | Path | None = None) -> Path:
    return Path(path or os.getenv("CIVICNODE_DB_PATH", DEFAULT_DATABASE))


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    resolved = database_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(resolved, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    return connection


@contextmanager
def managed_connection(
    path: str | Path | None = None,
) -> Iterator[sqlite3.Connection]:
    connection = connect(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def initialize_database(path: str | Path | None = None) -> None:
    with managed_connection(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                tracking_number TEXT NOT NULL UNIQUE,
                farmer_name TEXT NOT NULL,
                mobile TEXT NOT NULL,
                scheme TEXT NOT NULL CHECK (scheme IN ('flood_relief', 'land_acquisition')),
                incident_date TEXT NOT NULL,
                narrative TEXT NOT NULL DEFAULT '',
                survey_number TEXT,
                village TEXT,
                taluka TEXT,
                plot_json TEXT,
                flood_relief_json TEXT,
                land_acquisition_json TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                lane TEXT,
                amount TEXT,
                pipeline_json TEXT NOT NULL DEFAULT '{}',
                flags_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
            CREATE INDEX IF NOT EXISTS idx_claims_scheme_taluka ON claims(scheme, taluka);
            CREATE INDEX IF NOT EXISTS idx_claims_mobile ON claims(mobile);
            CREATE INDEX IF NOT EXISTS idx_claims_survey ON claims(survey_number, taluka);

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                content BLOB NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_documents_claim_id ON documents(claim_id);

            CREATE TABLE IF NOT EXISTS otp_challenges (
                claim_id TEXT PRIMARY KEY REFERENCES claims(id) ON DELETE CASCADE,
                code_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                verified_at TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                requested_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS registry (
                registry_id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                survey_number TEXT NOT NULL,
                village TEXT NOT NULL,
                taluka TEXT NOT NULL,
                area_ha TEXT NOT NULL,
                polygon_json TEXT,
                UNIQUE(survey_number, village, taluka)
            );

            CREATE TABLE IF NOT EXISTS claim_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_claim_events_claim_id
                ON claim_events(claim_id, event_id);
            """
        )
        _seed_registry(connection)


def _seed_registry(connection: sqlite3.Connection) -> None:
    rows = [
        ("DEMO-REG-001", "Ramesh P", "45/2", "Ponda", "Ponda", "1.2000",
         [[74.1395, 15.5345], [74.1405, 15.5345], [74.1405, 15.5355], [74.1395, 15.5355]]),
        ("DEMO-REG-002", "Sita Naik", "12/3", "Valpoi", "Sattari", "0.8500", None),
        ("DEMO-REG-003", "Arjun Dessai", "8/1", "Mapusa", "Bardez", "1.5000", None),
        ("DEMO-REG-004", "Meera Kamat", "22/4", "Quepem", "Quepem", "0.6250", None),
    ]
    for row in rows:
        connection.execute(
            """
            INSERT OR IGNORE INTO registry
                (registry_id, owner, survey_number, village, taluka, area_ha, polygon_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (*row[:6], json_dump(row[6]) if row[6] else None),
        )
