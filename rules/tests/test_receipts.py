
from rules.receipts.builder import build_receipt


def sample_calculation():
    return {
        "claim_id": "CLM-FLOOD-001",
        "scheme": "flood_relief",
        "incident_date": "2026-06-15",
        "rule_pack": {
            "version": "v1",
            "status": "demo",
            "sha256": "a" * 64,
        },
        "calculation": {
            "total": "2222.22",
            "currency": "INR",
            "formula": "eligible_area_hectares * rate_per_hectare",
        },
        "notices": ["Synthetic rate used."],
    }


def test_receipt_contains_required_fields():
    receipt = build_receipt(sample_calculation())

    assert receipt["claim_id"] == "CLM-FLOOD-001"
    assert receipt["scheme"] == "flood_relief"
    assert receipt["receipt_status"] == "demonstration"
    assert receipt["decision_status"] == "pending_officer_review"


def test_receipt_has_unique_id():
    first = build_receipt(sample_calculation())
    second = build_receipt(sample_calculation())

    assert first["receipt_id"] != second["receipt_id"]


def test_receipt_preserves_calculation():
    receipt = build_receipt(sample_calculation())

    assert receipt["calculation"]["total"] == "2222.22"
    assert receipt["calculation"]["currency"] == "INR"


def test_receipt_preserves_rule_pack_hash():
    receipt = build_receipt(sample_calculation())

    assert receipt["rule_pack"]["sha256"] == "a" * 64


def test_receipt_contains_disclaimers():
    receipt = build_receipt(sample_calculation())

    assert any(
        "not an official" in notice.lower()
        for notice in receipt["notices"]
    )


def test_receipt_rejects_missing_fields():
    try:
        build_receipt({"claim_id": "CLM-001"})
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Missing calculation fields" in str(exc)


def test_receipt_does_not_modify_original_result():
    original = sample_calculation()
    original_calculation = original["calculation"].copy()

    build_receipt(original)

    assert original["calculation"] == original_calculation
