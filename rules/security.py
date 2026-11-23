
import secrets

from fastapi import Header, HTTPException, status

from rules.config import settings


async def verify_internal_key(
    x_internal_key: str | None = Header(
        default=None,
        alias="X-Internal-Key",
    ),
) -> None:
    """
    Authenticate requests coming from trusted internal services.
    """

    configured_key = settings.internal_api_key

    # Fail closed if the application has no configured secret.
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AUTH_NOT_CONFIGURED",
                "message": "Internal API authentication is not configured.",
            },
        )

    # No key was supplied.
    if not x_internal_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "X-Internal-Key header is required.",
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Compare secrets safely without ordinary string comparison.
    if not secrets.compare_digest(
        x_internal_key.encode("utf-8"),
        configured_key.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INVALID_INTERNAL_KEY",
                "message": "The supplied internal API key is invalid.",
            },
        )
