from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.db import json_dump, managed_connection, now_utc
from backend.schemas import ClaimCreate, OfficerDecision

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _mobile(value: str) -> str:
    digits = "".join(char for char in value if char.isdigit())
    return digits[-10:]


def _claim_row(connection: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return row


def _serialize_claim(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    include_documents: bool = True,
) -> dict[str, Any]:
    result = dict(row)
    for column, key in (
        ("plot_json", "plot"),
        ("flood_relief_json", "flood_relief"),
        ("land_acquisition_json", "land_acquisition"),
        ("pipeline_json", "pipeline"),
        ("flags_json", "flags"),
    ):
        value = result.pop(column)
        result[key] = json.loads(value) if value else None
    if include_documents:
        documents = connection.execute(
            """
            SELECT id, filename, content_type, sha256, created_at
            FROM documents WHERE claim_id = ? ORDER BY created_at, id
            """,
            (row["id"],),
        ).fetchall()
        result["documents"] = [dict(document) for document in documents]
    return result


def get_claim(claim_id: str, path: str | Path | None = None) -> dict[str, Any]:
    with managed_connection(path) as connection:
        return _serialize_claim(connection, _claim_row(connection, claim_id))


def create_claim(body: ClaimCreate, path: str | Path | None = None) -> dict[str, Any]:
    claim_id = str(uuid.uuid4())
    tracking = f"GOA-{datetime.now(timezone.utc).year}-{claim_id[:8].upper()}"
    now = now_utc()
    values = body.model_dump(mode="json")
    mobile = _mobile(body.mobile)
    with managed_connection(path) as connection:
        connection.execute(
            """
            INSERT INTO claims (
                id, tracking_number, farmer_name, mobile, scheme, incident_date,
                narrative, survey_number, village, taluka, plot_json,
                land_acquisition_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id, tracking, body.farmer_name.strip(), mobile, body.scheme,
                body.incident_date.isoformat(), body.narrative, body.survey_number,
                body.village, body.taluka,
                json_dump(values["plot"]) if values["plot"] else None,
                json_dump(values["land_acquisition"]) if values["land_acquisition"] else None,
                now, now,
            ),
        )
        _add_event(connection, claim_id, "CLAIM_CREATED", "farmer", {"status": "draft"})
        return _serialize_claim(connection, _claim_row(connection, claim_id))


def _add_event(
    connection: sqlite3.Connection,
    claim_id: str,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO claim_events (claim_id, event_type, actor, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (claim_id, event_type, actor, json_dump(payload), now_utc()),
    )


def request_otp(claim_id: str, path: str | Path | None = None) -> dict[str, Any]:
    code = os.getenv("CIVICNODE_DEMO_OTP_CODE", "123456")
    if not os.getenv("CIVICNODE_DEMO_MODE", "true").lower() in {"1", "true", "yes"}:
        raise HTTPException(
            status_code=503,
            detail="No SMS gateway is configured; enable demo mode to use mock OTP.",
        )
    now = datetime.now(timezone.utc)
    with managed_connection(path) as connection:
        _claim_row(connection, claim_id)
        connection.execute(
            """
            INSERT INTO otp_challenges
                (claim_id, code_hash, expires_at, verified_at, attempts, requested_at)
            VALUES (?, ?, ?, NULL, 0, ?)
            ON CONFLICT(claim_id) DO UPDATE SET
                code_hash = excluded.code_hash,
                expires_at = excluded.expires_at,
                verified_at = NULL,
                attempts = 0,
                requested_at = excluded.requested_at
            """,
            (
                claim_id,
                hashlib.sha256(f"{claim_id}:{code}".encode()).hexdigest(),
                (now + timedelta(minutes=5)).isoformat(),
                now.isoformat(),
            ),
        )
        _add_event(connection, claim_id, "MOCK_OTP_REQUESTED", "system", {"delivery": "simulated"})
    return {
        "claim_id": claim_id,
        "delivery": "simulated",
        "expires_in_seconds": 300,
        "demo_code": code,
    }


def verify_otp(
    claim_id: str,
    code: str,
    path: str | Path | None = None,
) -> dict[str, Any]:
    with managed_connection(path) as connection:
        _claim_row(connection, claim_id)
        challenge = connection.execute(
            "SELECT * FROM otp_challenges WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        if challenge is None:
            raise HTTPException(status_code=409, detail="Request an OTP for this claim first.")
        if challenge["verified_at"]:
            return {"claim_id": claim_id, "verified": True}
        if challenge["attempts"] >= 5:
            raise HTTPException(status_code=429, detail="OTP attempt limit reached.")
        if datetime.fromisoformat(challenge["expires_at"]) <= datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="OTP expired; request a new code.")
        candidate = hashlib.sha256(f"{claim_id}:{code}".encode()).hexdigest()
        if not hmac.compare_digest(candidate, challenge["code_hash"]):
            connection.execute(
                "UPDATE otp_challenges SET attempts = attempts + 1 WHERE claim_id = ?",
                (claim_id,),
            )
            _add_event(connection, claim_id, "MOCK_OTP_REJECTED", "farmer", {})
            raise HTTPException(status_code=422, detail="OTP is incorrect.")
        verified_at = now_utc()
        connection.execute(
            "UPDATE otp_challenges SET verified_at = ? WHERE claim_id = ?",
            (verified_at, claim_id),
        )
        _add_event(connection, claim_id, "MOCK_OTP_VERIFIED", "farmer", {})
        return {"claim_id": claim_id, "verified": True}


def save_document(
    claim_id: str,
    filename: str,
    content: bytes,
    path: str | Path | None = None,
) -> dict[str, Any]:
    if not content:
        raise HTTPException(status_code=422, detail="Document is empty.")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB limit.")
    suffix = Path(filename or "").suffix.lower()
    content_type = ALLOWED_DOCUMENT_TYPES.get(suffix)
    if content_type is None:
        raise HTTPException(status_code=415, detail="Upload a PDF, PNG or JPEG document.")
    document_id = str(uuid.uuid4())
    created_at = now_utc()
    with managed_connection(path) as connection:
        _claim_row(connection, claim_id)
        connection.execute(
            """
            INSERT INTO documents
                (id, claim_id, filename, content_type, sha256, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id, claim_id, Path(filename).name, content_type,
                hashlib.sha256(content).hexdigest(), sqlite3.Binary(content), created_at,
            ),
        )
        _add_event(connection, claim_id, "DOCUMENT_UPLOADED", "farmer", {
            "document_id": document_id, "filename": Path(filename).name,
        })
    return {
        "id": document_id,
        "claim_id": claim_id,
        "filename": Path(filename).name,
        "content_type": content_type,
        "sha256": hashlib.sha256(content).hexdigest(),
        "created_at": created_at,
    }


def submit_claim(claim_id: str, path: str | Path | None = None) -> dict[str, Any]:
    with managed_connection(path) as connection:
        claim = _claim_row(connection, claim_id)
        otp = connection.execute(
            "SELECT verified_at FROM otp_challenges WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        if otp is None or otp["verified_at"] is None:
            raise HTTPException(status_code=409, detail="Verify the mobile number before submission.")
        if claim["status"] != "draft":
            raise HTTPException(status_code=409, detail="Only a draft claim can be submitted.")
        if not connection.execute(
            "SELECT 1 FROM documents WHERE claim_id = ? LIMIT 1", (claim_id,)
        ).fetchone():
            raise HTTPException(status_code=409, detail="Upload at least one land document first.")
        connection.execute(
            "UPDATE claims SET status = 'processing', updated_at = ? WHERE id = ?",
            (now_utc(), claim_id),
        )
        _add_event(connection, claim_id, "CLAIM_SUBMITTED", "farmer", {"status": "processing"})

    from backend.pipeline import run_pipeline

    return run_pipeline(claim_id, path)


def update_claim(
    claim_id: str,
    updates: dict[str, Any],
    path: str | Path | None = None,
) -> None:
    allowed = {
        "survey_number", "village", "taluka", "status", "lane", "amount",
        "pipeline_json", "flags_json", "updated_at",
    }
    if not updates or not set(updates).issubset(allowed):
        raise ValueError("Invalid claim update fields.")
    assignments = ", ".join(f"{key} = ?" for key in updates)
    with managed_connection(path) as connection:
        _claim_row(connection, claim_id)
        connection.execute(
            f"UPDATE claims SET {assignments} WHERE id = ?",
            (*updates.values(), claim_id),
        )


def update_pipeline_state(
    claim_id: str,
    status: str,
    lane: str | None,
    pipeline: dict[str, Any],
    flags: list[str] | None = None,
    amount: str | None = None,
    survey_number: str | None = None,
    village: str | None = None,
    taluka: str | None = None,
    path: str | Path | None = None,
) -> None:
    with managed_connection(path) as connection:
        _claim_row(connection, claim_id)
        connection.execute(
            """
            UPDATE claims
            SET status = ?, lane = ?, pipeline_json = ?, flags_json = ?,
                amount = ?, survey_number = COALESCE(?, survey_number),
                village = COALESCE(?, village), taluka = COALESCE(?, taluka),
                updated_at = ?
            WHERE id = ?
            """,
            (
                status, lane, json_dump(pipeline), json_dump(flags or []),
                amount, survey_number, village, taluka, now_utc(), claim_id,
            ),
        )
        _add_event(
            connection, claim_id, "PIPELINE_PROGRESS",
            "system", {"status": status, "current_stage": pipeline.get("current_stage")},
        )


def mark_interrupted_claims(path: str | Path | None = None) -> int:
    with managed_connection(path) as connection:
        rows = connection.execute(
            "SELECT id, pipeline_json FROM claims WHERE status = 'processing'"
        ).fetchall()
        for row in rows:
            pipeline = json.loads(row["pipeline_json"] or "{}")
            pipeline["status"] = "interrupted"
            pipeline["error"] = "The service restarted during automated checks."
            connection.execute(
                """
                UPDATE claims SET status = 'needs_review', lane = 'AMBER',
                    pipeline_json = ?, flags_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    json_dump(pipeline), json_dump(["PIPELINE_INTERRUPTED"]),
                    now_utc(), row["id"],
                ),
            )
            _add_event(
                connection, row["id"], "PIPELINE_INTERRUPTED", "system",
                {"status": "needs_review", "lane": "AMBER"},
            )
        return len(rows)


def decide_claim(
    claim_id: str,
    decision: OfficerDecision,
    path: str | Path | None = None,
) -> dict[str, Any]:
    statuses = {
        "approve": "approved",
        "request_information": "info_requested",
        "field_inspection": "field_inspection",
        "reject": "rejected",
    }
    with managed_connection(path) as connection:
        claim = _claim_row(connection, claim_id)
        if claim["status"] not in {
            "ready_for_officer", "needs_review", "info_requested", "field_inspection",
        }:
            raise HTTPException(status_code=409, detail="This claim is not awaiting an officer decision.")
        if decision.decision == "reject" and not decision.reason.strip():
            raise HTTPException(status_code=422, detail="A rejection reason is required.")
        if (
            decision.decision == "approve"
            and claim["lane"] != "GREEN"
            and not decision.reason.strip()
        ):
            raise HTTPException(
                status_code=422,
                detail="Add an override reason before approving a flagged claim.",
            )
        status = statuses[decision.decision]
        connection.execute(
            "UPDATE claims SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_utc(), claim_id),
        )
        _add_event(
            connection, claim_id, "OFFICER_DECISION", decision.officer_id,
            {"decision": decision.decision, "status": status, "reason": decision.reason},
        )
        return _serialize_claim(connection, _claim_row(connection, claim_id))


def list_claims(
    path: str | Path | None = None,
    scheme: str | None = None,
    status: str | None = None,
    lane: str | None = None,
    taluka: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    filters: list[str] = []
    values: list[Any] = []
    for column, value in (("scheme", scheme), ("status", status), ("lane", lane), ("taluka", taluka)):
        if value is not None:
            filters.append(f"{column} = ?")
            values.append(value)
    where = f" WHERE {' AND '.join(filters)}" if filters else ""
    with managed_connection(path) as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM claims{where}", values
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT * FROM claims{where}
            ORDER BY created_at DESC, id LIMIT ? OFFSET ?
            """,
            (*values, limit, offset),
        ).fetchall()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [_serialize_claim(connection, row) for row in rows],
        }


def dashboard_analytics(path: str | Path | None = None) -> dict[str, Any]:
    with managed_connection(path) as connection:
        total = connection.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        statuses = {
            row["status"]: row["count"]
            for row in connection.execute(
                "SELECT status, COUNT(*) AS count FROM claims GROUP BY status"
            )
        }
        by_scheme = [
            dict(row) for row in connection.execute(
                """
                SELECT scheme, status, lane, COUNT(*) AS count
                FROM claims GROUP BY scheme, status, lane ORDER BY scheme, status, lane
                """
            )
        ]
        by_taluka = [
            dict(row) for row in connection.execute(
                """
                SELECT COALESCE(taluka, 'Unknown') AS taluka, status, COUNT(*) AS count
                FROM claims GROUP BY taluka, status ORDER BY taluka, status
                """
            )
        ]
        flagged = connection.execute(
            "SELECT COUNT(*) FROM claims WHERE lane IN ('AMBER', 'RED')"
        ).fetchone()[0]
        stuck = connection.execute(
            """
            SELECT COUNT(*) FROM claims
            WHERE status = 'processing' AND updated_at < ?
            """,
            ((datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),),
        ).fetchone()[0]
        return {
            "total": total,
            "by_status": statuses,
            "by_scheme": by_scheme,
            "by_taluka": by_taluka,
            "flagged": flagged,
            "stuck": stuck,
            "automated_approval": False,
        }


def claim_events(claim_id: str, path: str | Path | None = None) -> list[dict[str, Any]]:
    with managed_connection(path) as connection:
        _claim_row(connection, claim_id)
        rows = connection.execute(
            "SELECT * FROM claim_events WHERE claim_id = ? ORDER BY event_id",
            (claim_id,),
        ).fetchall()
        result = []
        for row in rows:
            event = dict(row)
            event["payload"] = json.loads(event.pop("payload_json"))
            result.append(event)
        return result

