
from datetime import date, datetime
from decimal import Decimal

from rules.errors import CalculationError
from rules.calculator.rounding import round_money, to_decimal


def _validate_non_negative(value, field_name: str) -> Decimal:
    amount = to_decimal(value)

    if amount < 0:
        raise CalculationError(
            f"{field_name} cannot be negative."
        )

    return amount


def calculate_land_acquisition(
    land_value: str | Decimal | int,
    structures: list[dict],
    trees: list[dict],
    solatium_rate: str | Decimal | int,
    interest_rate_annual: str | Decimal | int,
    interest_start_date: date,
    interest_end_date: date,
    interest_basis_days: int = 365,
) -> dict:
    """
    Calculate a configurable DEMO land acquisition breakdown.

    Illustrative formula:
        Base value = land + structures + trees
        Solatium = base value * solatium rate
        Interest = (base value + solatium) *
                   annual interest rate * days / basis

    These formulas are configurable demonstration assumptions,
    NOT verified legal compensation rules.
    """

    land = _validate_non_negative(land_value, "Land value")

    solatium_rate = to_decimal(solatium_rate)
    interest_rate = to_decimal(interest_rate_annual)

    if not Decimal("0") <= solatium_rate <= Decimal("1"):
        raise CalculationError(
            "Solatium rate must be between 0 and 1."
        )

    if interest_rate < 0:
        raise CalculationError(
            "Interest rate cannot be negative."
        )

    if (
        isinstance(interest_basis_days, bool)
        or not isinstance(interest_basis_days, int)
        or interest_basis_days <= 0
    ):
        raise CalculationError(
            "Interest basis days must be a positive integer."
        )

    if (
    not isinstance(interest_start_date, date)
    or isinstance(interest_start_date, datetime)
    or not isinstance(interest_end_date, date)
    or isinstance(interest_end_date, datetime)
    ):
        raise CalculationError(
            "Interest dates must be valid date objects."
       )

    if interest_end_date < interest_start_date:
        raise CalculationError(
            "Interest end date cannot precede start date."
        )

    if not isinstance(structures, list) or not isinstance(trees, list):
        raise CalculationError(
            "Structures and trees must be lists."
        )

    structure_total = Decimal("0")
    structure_items = []

    for index, structure in enumerate(structures):
        if not isinstance(structure, dict) or "value" not in structure:
            raise CalculationError(
                f"Structure item {index} must contain a value."
            )

        value = _validate_non_negative(
            structure["value"],
            f"Structure {index} value",
        )

        structure_total += value

        structure_items.append({
            "description": str(
                structure.get("description", f"Structure {index + 1}")
            ),
            "value": str(value),
        })

    tree_total = Decimal("0")
    tree_items = []

    for index, tree in enumerate(trees):
        if not isinstance(tree, dict) or "value" not in tree:
            raise CalculationError(
                f"Tree item {index} must contain a value."
            )

        value = _validate_non_negative(
            tree["value"],
            f"Tree {index} value",
        )

        tree_total += value

        tree_items.append({
            "description": str(
                tree.get("description", f"Tree {index + 1}")
            ),
            "value": str(value),
        })

    base_value = land + structure_total + tree_total

    solatium_amount = base_value * solatium_rate
    interest_days = (
        interest_end_date - interest_start_date
    ).days

    interest_principal = base_value + solatium_amount

    interest_amount = (
        interest_principal
        * interest_rate
        * Decimal(interest_days)
        / Decimal(interest_basis_days)
    )

    total_before_rounding = (
        base_value + solatium_amount + interest_amount
    )

    total = round_money(total_before_rounding)

    return {
        "scheme": "land_acquisition",
        "currency": "INR",
        "line_items": [
            {
                "component": "land",
                "amount": str(round_money(land)),
            },
            {
                "component": "structures",
                "amount": str(round_money(structure_total)),
                "items": structure_items,
            },
            {
                "component": "trees",
                "amount": str(round_money(tree_total)),
                "items": tree_items,
            },
            {
                "component": "solatium",
                "rate": str(solatium_rate),
                "amount": str(round_money(solatium_amount)),
            },
            {
                "component": "interest",
                "annual_rate": str(interest_rate),
                "principal": str(interest_principal),
                "days": interest_days,
                "basis_days": interest_basis_days,
                "amount": str(round_money(interest_amount)),
            },
        ],
        "formula": (
            "land + structures + trees "
            "+ solatium + simple_interest"
        ),
        "base_value": str(round_money(base_value)),
        "total_before_rounding": str(total_before_rounding),
        "total": str(total),
        "rounding": "ROUND_HALF_UP",
        "notices": [
            "DEMO CALCULATION: All rates and formulas are illustrative.",
            "Not an official Government of Goa compensation determination.",
            "Interest and solatium methodology must be verified "
            "against applicable legal provisions before production use.",
        ],
    }
