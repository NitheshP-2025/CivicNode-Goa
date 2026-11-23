
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import rules.security as security


@pytest.fixture
def configured_settings(monkeypatch):
    monkeypatch.setattr(
        security,
        "settings",
        SimpleNamespace(internal_api_key="test-secret-key"),
    )


def test_valid_internal_key(configured_settings):
    result = asyncio.run(
        security.verify_internal_key("test-secret-key")
    )

    assert result is None


def test_missing_internal_key(configured_settings):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.verify_internal_key(None))

    assert exc.value.status_code == 401


def test_invalid_internal_key(configured_settings):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.verify_internal_key("wrong-key"))

    assert exc.value.status_code == 403


def test_authentication_not_configured(monkeypatch):
    monkeypatch.setattr(
        security,
        "settings",
        SimpleNamespace(internal_api_key=None),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.verify_internal_key("some-key"))

    assert exc.value.status_code == 503
