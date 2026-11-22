"""Unit tests for app.schemas.user."""

import pytest
from pydantic import ValidationError

from app.schemas.user import LoginRequest, OAuthVerifyRequest, RegisterRequest


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


def test_register_and_login_request_validation():
    reg = RegisterRequest(
        name="  <b>Alex</b>\x00  ",
        email="Alex@Example.COM",
        password="Password1",
    )
    assert reg.name == "Alex"
    assert reg.email == "alex@example.com"

    with pytest.raises(ValidationError):
        RegisterRequest(name="Alex", email="a@b.com", password="short")

    with pytest.raises(ValidationError):
        RegisterRequest(name="Alex", email="a@b.com", password="onlyletters")

    with pytest.raises(ValidationError):
        RegisterRequest(name="Alex", email="a@b.com", password="12345678")

    login = LoginRequest(email="USER@EXAMPLE.COM", password="Password1")
    assert login.email == "user@example.com"
