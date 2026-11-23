
from decimal import Decimal

import pytest

from rules.calculator.rounding import (
    to_decimal,
    round_money,
    format_inr,
)


def test_round_money_to_two_decimal_places():
    assert round_money("125.456") == Decimal("125.46")


def test_round_half_up():
    assert round_money("125.455") == Decimal("125.46")


def test_round_down_when_third_digit_is_below_five():
    assert round_money("125.454") == Decimal("125.45")


def test_round_negative_amount():
    assert round_money("-125.455") == Decimal("-125.46")


def test_format_inr():
    assert format_inr("1388.9") == "1388.90"


def test_integer_conversion():
    assert to_decimal(100) == Decimal("100")


def test_float_is_rejected():
    with pytest.raises(TypeError):
        to_decimal(125.45)


def test_non_finite_value_is_rejected():
    with pytest.raises(ValueError):
        round_money("NaN")
