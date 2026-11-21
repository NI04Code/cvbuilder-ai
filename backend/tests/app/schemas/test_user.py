"""Unit tests for app.schemas.user."""

import pytest
from pydantic import ValidationError

from app.schemas.user import OAuthVerifyRequest


def test_oauth_verify_request_validation():
    ok = OAuthVerifyRequest(
        email="user@example.com",
        name="Alex",
        provider="google",
        provider_account_id="123",
    )
    assert ok.provider == "google"

    with pytest.raises(ValidationError):
        OAuthVerifyRequest(
            email="not-an-email",
            name="Alex",
            provider="facebook",
            provider_account_id="123",
        )
