
from rules.errors import (
    RulesServiceError,
    RulePackNotFoundError,
    CalculationError,
    DuplicateReceiptError,
)


def test_base_error():
    error = RulesServiceError(
        code="TEST_ERROR",
        message="Test message",
        status_code=400,
    )

    assert error.code == "TEST_ERROR"
    assert error.status_code == 400


def test_rule_pack_not_found():
    error = RulePackNotFoundError("flood_relief", "v1")

    assert error.code == "RULE_PACK_NOT_FOUND"
    assert error.status_code == 404


def test_calculation_error():
    error = CalculationError("Invalid calculation")

    assert error.code == "CALCULATION_ERROR"
    assert error.status_code == 422


def test_duplicate_receipt_error():
    error = DuplicateReceiptError("GOA-001", 1)

    assert error.code == "RECEIPT_REVISION_CONFLICT"
    assert error.status_code == 409
