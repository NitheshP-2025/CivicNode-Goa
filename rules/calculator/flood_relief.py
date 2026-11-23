
from decimal import Decimal

from rules.errors import CalculationError
from rules.calculator.rounding import round_money, to_decimal


# Physical unit conversions, not government policy values.
AREA_TO_SQUARE_METRES = {
    "hectare": Decimal("10000"),
    "are": Decimal("100"),
    "sq_m": Decimal("1"),
}

SQUARE_METRES_PER_HECTARE = Decimal("10000")


def convert_to_hectares(
    area: str | Decimal | int,
    unit: str,
) -> Decimal:
    """Convert an area measurement into hectares."""

    if unit not in AREA_TO_SQUARE_METRES:
        raise CalculationError(
            f"Unsupported area unit: {unit}"
        )

    area_value = to_decimal(area)

    if area_value <= 0:
        raise CalculationError(
            "Eligible area must be greater than zero."
        )

    square_metres = (
        area_value * AREA_TO_SQUARE_METRES[unit]
    )

    return square_metres / SQUARE_METRES_PER_HECTARE


def calculate_flood_relief(
    eligible_area: str | Decimal | int,
    area_unit: str,
    rate_per_hectare: str | Decimal | int,
) -> dict:
    """
    Calculate demo flood relief using:

        Compensation = Eligible area in hectares
                       × Rate per hectare

    This function performs arithmetic only.
    It does not determine legal eligibility.
    """

    try:
        rate = to_decimal(rate_per_hectare)
        area_hectares = convert_to_hectares(
            eligible_area,
            area_unit,
        )

        if rate < 0:
            raise CalculationError(
                "Compensation rate cannot be negative."
            )

        raw_amount = area_hectares * rate
        total = round_money(raw_amount)

        return {
            "scheme": "flood_relief",
            "eligible_area": {
                "value": str(eligible_area),
                "unit": area_unit,
            },
            "normalized_area_hectares": str(
                area_hectares
            ),
            "rate_per_hectare": str(rate),
            "formula": (
                "eligible_area_hectares "
                "* rate_per_hectare"
            ),
            "raw_amount": str(raw_amount),
            "total": str(total),
            "currency": "INR",
            "rounding": "ROUND_HALF_UP",
            "notices": [
                "DEMO CALCULATION: Synthetic rate used.",
                "This calculation is not an official "
                "Government of Goa compensation determination.",
            ],
        }

    except CalculationError:
        raise

    except (ValueError, TypeError) as exc:
        raise CalculationError(
            "Invalid input supplied to flood relief calculator."
        ) from exc
