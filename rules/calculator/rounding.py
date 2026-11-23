
from decimal import Decimal, ROUND_HALF_UP


INR_PRECISION = Decimal("0.01")
ROUNDING_MODE = ROUND_HALF_UP


def to_decimal(value: str | Decimal | int) -> Decimal:
    """
    Convert supported numeric inputs into Decimal.

    Floats are deliberately rejected to avoid precision loss.
    """

    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("Use Decimal, string or integer values.")

    try:
        result = Decimal(value)
    except Exception as exc:
        raise ValueError("Invalid decimal value.") from exc

    if not result.is_finite():
        raise ValueError("Decimal value must be finite.")

    return result


def round_money(amount: str | Decimal | int) -> Decimal:
    """
    Round a monetary amount to two decimal places
    using ROUND_HALF_UP.
    """

    decimal_amount = to_decimal(amount)

    return decimal_amount.quantize(
        INR_PRECISION,
        rounding=ROUNDING_MODE,
    )


def format_inr(amount: str | Decimal | int) -> str:
    """Return a two-decimal monetary value as a string."""

    return f"{round_money(amount):.2f}"
