
from typing import Any


class RulesServiceError(Exception):
    """Base exception for all expected Rules service errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)

        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class RulePackNotFoundError(RulesServiceError):
    def __init__(self, scheme: str, version: str | None = None):
        super().__init__(
            code="RULE_PACK_NOT_FOUND",
            message="The requested rule pack could not be found.",
            status_code=404,
            details={
                "scheme": scheme,
                "version": version,
            },
        )


class CalculationError(RulesServiceError):
    def __init__(self, message: str, details=None):
        super().__init__(
            code="CALCULATION_ERROR",
            message=message,
            status_code=422,
            details=details,
        )


class DuplicateReceiptError(RulesServiceError):
    def __init__(self, claim_id: str, revision: int):
        super().__init__(
            code="RECEIPT_REVISION_CONFLICT",
            message="This claim revision already exists with different content.",
            status_code=409,
            details={
                "claim_id": claim_id,
                "revision": revision,
            },
        )
