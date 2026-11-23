
from datetime import date

from rules.engine.loader import load_rule_pack


def test_load_land_acquisition_demo_pack():
    pack = load_rule_pack(
        scheme="land_acquisition",
        version="v1",
        incident_date=date(2026, 6, 15),
    )

    assert pack["scheme"] == "land_acquisition"
    assert pack["version"] == "v1"
    assert pack["status"] == "demo"


def test_land_acquisition_pack_has_calculation_config():
    pack = load_rule_pack(
        scheme="land_acquisition",
        version="v1",
        incident_date=date(2026, 6, 15),
    )

    calculation = pack["calculation"]

    assert calculation["method"] == "illustrative_land_acquisition"
    assert calculation["solatium_rate"] == "0.10"
    assert calculation["interest_rate_annual"] == "0.05"
    assert calculation["interest_basis_days"] == 365


def test_land_acquisition_pack_has_hash():
    pack = load_rule_pack(
        scheme="land_acquisition",
        version="v1",
        incident_date=date(2026, 6, 15),
    )

    assert len(pack["_sha256"]) == 64
