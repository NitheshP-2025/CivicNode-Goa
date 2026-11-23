
import hashlib
import json

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from rules.config import settings
from rules.errors import RulePackNotFoundError, RulesServiceError


SUPPORTED_SCHEMES = {
    "flood_relief",
    "land_acquisition",
}


def calculate_pack_hash(pack: dict[str, Any]) -> str:
    """Generate a deterministic SHA-256 hash for a rule pack."""

    def serialize_dates(value):
        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, dict):
            return {
                key: serialize_dates(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [serialize_dates(item) for item in value]

        return value

    canonical_pack = serialize_dates(pack)

    canonical_content = json.dumps(
        canonical_pack,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(canonical_content).hexdigest()


def load_rule_pack(
    scheme: str,
    version: str | None = None,
    incident_date: date | None = None,
) -> dict[str, Any]:
    """
    Load and validate a YAML rule pack.

    If a version is supplied, load that exact version.
    If an incident date is supplied, validate its effective period.
    Without a version, select the pack effective on the incident date.
    """

    if scheme not in SUPPORTED_SCHEMES:
        raise RulesServiceError(
            code="UNSUPPORTED_SCHEME",
            message=f"Unsupported scheme: {scheme}",
            status_code=422,
        )

    if incident_date is not None and not isinstance(incident_date, date):
        raise RulesServiceError(
            code="INVALID_INCIDENT_DATE",
            message="Incident date must be a valid date.",
            status_code=422,
        )

    packs_dir = Path(settings.packs_dir)

    if not packs_dir.exists():
        raise RulePackNotFoundError(scheme, version)

    if version:
        if not version.replace("_", "").isalnum():
            raise RulesServiceError(
                code="INVALID_RULE_VERSION",
                message="Invalid rule version format.",
                status_code=422,
            )

        candidates = [
            packs_dir / f"{scheme}_{version}.yaml"
        ]
    else:
        candidates = sorted(
            packs_dir.glob(f"{scheme}_*.yaml")
        )

    valid_packs = []

    for path in candidates:
        if not path.is_file():
            continue

        try:
            with path.open("r", encoding="utf-8") as file:
                pack = yaml.safe_load(file)

        except yaml.YAMLError as exc:
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"Invalid YAML in {path.name}.",
                status_code=500,
            ) from exc

        if not isinstance(pack, dict):
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"Rule pack {path.name} must contain a YAML object.",
                status_code=500,
            )

        required_fields = {
            "scheme",
            "version",
            "status",
            "effective_from",
            "effective_to",
            "source_documents",
        }

        if not required_fields.issubset(pack):
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"Rule pack {path.name} is missing required metadata.",
                status_code=500,
            )

        if pack["scheme"] != scheme:
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"Scheme mismatch in {path.name}.",
                status_code=500,
            )

        if not isinstance(pack["version"], str) or not pack["version"]:
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"Invalid version metadata in {path.name}.",
                status_code=500,
            )

        if pack["status"] not in {"demo", "verified"}:
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"Invalid status in {path.name}.",
                status_code=500,
            )

        if not isinstance(pack["source_documents"], list):
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"source_documents must be a list in {path.name}.",
                status_code=500,
            )

        try:
            effective_from = date.fromisoformat(
                str(pack["effective_from"])
            )

            effective_to = (
                date.fromisoformat(str(pack["effective_to"]))
                if pack["effective_to"] is not None
                else None
            )

        except (ValueError, TypeError) as exc:
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"Invalid effective dates in {path.name}.",
                status_code=500,
            ) from exc

        if effective_to and effective_to < effective_from:
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"Invalid effective date range in {path.name}.",
                status_code=500,
            )

        pack["_file_name"] = path.name
        pack["_effective_from"] = effective_from
        pack["_effective_to"] = effective_to
        pack["_sha256"] = calculate_pack_hash(pack)

        if version and pack["version"] != version:
            raise RulesServiceError(
                code="INVALID_RULE_PACK",
                message=f"Version mismatch in {path.name}.",
                status_code=500,
            )

        # Explicit version: validate the requested incident date.
        if version:
            if incident_date is not None and not (
                effective_from <= incident_date
                and (
                    effective_to is None
                    or incident_date <= effective_to
                )
            ):
                raise RulesServiceError(
                    code="RULE_VERSION_NOT_EFFECTIVE",
                    message=(
                        f"Rule version {version} is not effective "
                        f"for incident date {incident_date.isoformat()}."
                    ),
                    status_code=422,
                )

            return pack

        # Automatic version selection requires an incident date.
        if incident_date is None:
            raise RulesServiceError(
                code="INCIDENT_DATE_REQUIRED",
                message=(
                    "Incident date is required when selecting "
                    "a rule version."
                ),
                status_code=422,
            )

        if (
            effective_from <= incident_date
            and (
                effective_to is None
                or incident_date <= effective_to
            )
        ):
            valid_packs.append(pack)

    if not valid_packs:
        raise RulePackNotFoundError(scheme, version)

    if len(valid_packs) > 1:
        raise RulesServiceError(
            code="AMBIGUOUS_RULE_VERSION",
            message="Multiple rule packs match the incident date.",
            status_code=409,
        )

    return valid_packs[0]
