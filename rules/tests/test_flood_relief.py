
from decimal import Decimal

import pytest

from rules.calculator.flood_relief import (
    convert_to_hectares,
    calculate_flood_relief,
)
from rules.errors import CalculationError


def test_hectare_conversion():
    assert convert_to_hectares(
        "1.5", "hectare"
    ) == Decimal("1.5")


def test_are_conversion():
    assert convert_to_hectares(
        "100", "are"
    ) == Decimal("1")


def test_square_metre_conversion():
    assert convert_to_hectares(
        "10000", "sq_m"
    ) == Decimal("1")


def test_flood_relief_calculation():
    result = calculate_flood_relief(
        eligible_area="1.2500",
        area_unit="hectare",
        rate_per_hectare="1111.11",
    )

    assert result["total"] == "1388.89"
    assert result["currency"] == "INR"


def test_calculation_with_are():
    result = calculate_flood_relief(
        eligible_area="100",
        area_unit="are",
        rate_per_hectare="1000",
    )

    assert result["total"] == "1000.00"


def test_zero_area_is_rejected():
    with pytest.raises(CalculationError):
        calculate_flood_relief(
            "0", "hectare", "1000"
        )


def test_negative_rate_is_rejected():
    with pytest.raises(CalculationError):
        calculate_flood_relief(
            "1", "hectare", "-1000"
        )


def test_unsupported_area_unit_is_rejected():
    with pytest.raises(CalculationError):
        calculate_flood_relief(
            "1", "acre", "1000"
        )


def test_calculation_returns_formula():
    result = calculate_flood_relief(
        "1", "hectare", "1000"
    )

    assert result["formula"] == (
        "eligible_area_hectares * rate_per_hectare"
    )


def test_calculation_has_demo_notice():
    result = calculate_flood_relief(
        "1", "hectare", "1000"
    )

    assert any(
        "DEMO CALCULATION" in notice
        for notice in result["notices"]
    )


def test_negative_area_is_rejected():
    with pytest.raises(CalculationError):
        calculate_flood_relief(
            "-1", "hectare", "1000"
        )


@pytest.mark.parametrize(
    "invalid_value",
    [
        "abc",
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_invalid_numeric_values_are_rejected(invalid_value):
    with pytest.raises(CalculationError):
        calculate_flood_relief(
            "1", "hectare", invalid_value
        )


@pytest.mark.parametrize(
    "invalid_value",
    [
        1.5,
        True,
        False,
    ],
)
def test_unsupported_numeric_types_are_rejected(invalid_value):
    with pytest.raises(CalculationError):
        calculate_flood_relief(
            invalid_value, "hectare", "1000"
        )


def test_zero_rate_is_allowed():
    result = calculate_flood_relief(
        "1", "hectare", "0"
    )

    assert result["total"] == "0.00"


def test_half_cent_uses_half_up_rounding():
    result = calculate_flood_relief(
        "1", "hectare", "0.005"
    )

    assert result["total"] == "0.01"


def test_very_small_positive_area_is_accepted():
    result = calculate_flood_relief(
        "0.0001", "hectare", "1000"
    )

    assert result["total"] == "0.10"
