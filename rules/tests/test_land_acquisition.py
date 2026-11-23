
from datetime import date

import pytest

from rules.calculator.land_acquisition import calculate_land_acquisition
from rules.errors import CalculationError


def make_calculation(**overrides):
    inputs = {
        "land_value": "100000",
        "structures": [
            {"description": "House", "value": "20000"},
            {"description": "Shed", "value": "5000"},
        ],
        "trees": [
            {"description": "Mango tree", "value": "3000"},
        ],
        "solatium_rate": "0.10",
        "interest_rate_annual": "0.05",
        "interest_start_date": date(2026, 1, 1),
        "interest_end_date": date(2027, 1, 1),
        "interest_basis_days": 365,
    }

    inputs.update(overrides)
    return calculate_land_acquisition(**inputs)


def test_all_five_components_are_returned():
    result = make_calculation()

    components = {
        item["component"]
        for item in result["line_items"]
    }

    assert components == {
        "land", "structures", "trees",
        "solatium", "interest",
    }


def test_base_value():
    assert make_calculation()["base_value"] == "128000.00"


def test_solatium_amount():
    result = make_calculation()
    item = next(
        x for x in result["line_items"]
        if x["component"] == "solatium"
    )
    assert item["amount"] == "12800.00"


def test_interest_amount():
    result = make_calculation()
    item = next(
        x for x in result["line_items"]
        if x["component"] == "interest"
    )
    assert item["amount"] == "7040.00"


def test_total_amount():
    assert make_calculation()["total"] == "147840.00"


def test_empty_structures_and_trees():
    result = make_calculation(
        structures=[],
        trees=[],
        solatium_rate="0",
        interest_rate_annual="0",
    )
    assert result["base_value"] == "100000.00"
    assert result["total"] == "100000.00"


def test_negative_land_value_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(land_value="-100")


def test_negative_structure_value_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(structures=[{"value": "-500"}])


def test_negative_tree_value_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(trees=[{"value": "-500"}])


def test_invalid_solatium_rate_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(solatium_rate="1.5")


def test_negative_interest_rate_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(interest_rate_annual="-0.05")


def test_invalid_interest_dates_are_rejected():
    with pytest.raises(CalculationError):
        make_calculation(
            interest_start_date=date(2027, 1, 1),
            interest_end_date=date(2026, 1, 1),
        )


def test_demo_notice_is_returned():
    result = make_calculation()
    assert any(
        "DEMO CALCULATION" in notice
        for notice in result["notices"]
    )


def test_float_inputs_are_rejected():
    with pytest.raises(TypeError):
        make_calculation(land_value=100000.50)



def test_zero_interest_period():
    result = make_calculation(
        interest_start_date=date(2026, 1, 1),
        interest_end_date=date(2026, 1, 1),
    )

    interest = next(
        x for x in result["line_items"]
        if x["component"] == "interest"
    )

    assert interest["days"] == 0
    assert interest["amount"] == "0.00"


def test_maximum_solatium_rate_is_allowed():
    result = make_calculation(solatium_rate="1")

    solatium = next(
        x for x in result["line_items"]
        if x["component"] == "solatium"
    )

    assert solatium["amount"] == "128000.00"


def test_zero_solatium_rate_is_allowed():
    result = make_calculation(solatium_rate="0")

    solatium = next(
        x for x in result["line_items"]
        if x["component"] == "solatium"
    )

    assert solatium["amount"] == "0.00"


def test_invalid_interest_start_date_type_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(interest_start_date="2026-01-01")


def test_invalid_interest_end_date_type_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(interest_end_date="2027-01-01")


def test_datetime_is_rejected_as_interest_date():
    from datetime import datetime

    with pytest.raises(CalculationError):
        make_calculation(
            interest_start_date=datetime(2026, 1, 1)
        )


def test_structures_must_be_a_list():
    with pytest.raises(CalculationError):
        make_calculation(structures="invalid")


def test_trees_must_be_a_list():
    with pytest.raises(CalculationError):
        make_calculation(trees="invalid")


def test_structure_without_value_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(
            structures=[{"description": "House"}]
        )


def test_tree_without_value_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(
            trees=[{"description": "Mango tree"}]
        )


def test_boolean_interest_basis_is_rejected():
    with pytest.raises(CalculationError):
        make_calculation(interest_basis_days=True)
