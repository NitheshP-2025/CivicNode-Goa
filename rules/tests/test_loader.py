
from datetime import date

import pytest

from rules.engine.loader import (
    calculate_pack_hash,
    load_rule_pack,
)
from rules.errors import RulesServiceError


def test_load_demo_rule_pack():
    pack = load_rule_pack(
        scheme="flood_relief",
        version="v1",
    )

    assert pack["scheme"] == "flood_relief"
    assert pack["version"] == "v1"
    assert pack["status"] == "demo"


def test_pack_has_sha256_hash():
    pack = load_rule_pack("flood_relief", "v1")

    assert len(pack["_sha256"]) == 64


def test_hash_is_deterministic():
    sample = {"scheme": "flood_relief", "version": "v1"}

    assert calculate_pack_hash(sample) == calculate_pack_hash(sample)


def test_unsupported_scheme_is_rejected():
    with pytest.raises(RulesServiceError) as exc:
        load_rule_pack("unknown_scheme", "v1")

    assert exc.value.code == "UNSUPPORTED_SCHEME"


def test_incident_date_selects_effective_pack():
    pack = load_rule_pack(
        scheme="flood_relief",
        incident_date=date(2026, 6, 15),
    )

    assert pack["version"] == "v1"



def test_explicit_version_accepts_effective_incident_date():
    pack = load_rule_pack(
        scheme="flood_relief",
        version="v1",
        incident_date=date(2026, 6, 15),
    )

    assert pack["version"] == "v1"


def test_explicit_version_rejects_incident_before_effective_date():
    with pytest.raises(RulesServiceError) as exc:
        load_rule_pack(
            scheme="flood_relief",
            version="v1",
            incident_date=date(2025, 12, 31),
        )

    assert exc.value.code == "RULE_VERSION_NOT_EFFECTIVE"


def test_open_ended_version_accepts_future_incident_date():
    pack = load_rule_pack(
        scheme="flood_relief",
        version="v1",
        incident_date=date(2030, 1, 1),
    )

    assert pack["version"] == "v1"


def test_invalid_incident_date_type_is_rejected():
    with pytest.raises(RulesServiceError) as exc:
        load_rule_pack(
            scheme="flood_relief",
            version="v1",
            incident_date="2026-06-15",
        )

    assert exc.value.code == "INVALID_INCIDENT_DATE"
