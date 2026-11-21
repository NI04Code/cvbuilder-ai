"""Unit tests for app.api.auth."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.api.auth import verify_internal_auth_secret
from app.core import settings
from app.database import get_db
from app.main import app
from app.schemas.user import TokenResponse, UserResponse
from app.security.jwt import get_current_user
from tests.conftest import make_user


def test_verify_internal_auth_secret_branches(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "internal_auth_secret", "")
    with pytest.raises(HTTPException) as exc:
        verify_internal_auth_secret(None)
    assert exc.value.status_code == 500

    monkeypatch.setattr(settings, "environment", "development")
    verify_internal_auth_secret(None)  # Allowed with warning in dev

    monkeypatch.setattr(settings, "internal_auth_secret", "top-secret")
    with pytest.raises(HTTPException) as exc2:
        verify_internal_auth_secret("wrong")
    assert exc2.value.status_code == 401
    verify_internal_auth_secret("top-secret")


@pytest.mark.asyncio
async def test_auth_endpoints(mock_db, monkeypatch):
    monkeypatch.setattr(settings, "internal_auth_secret", "top-secret")
    user = make_user()
    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=True,
        has_profile=True,
        created_at=user.created_at,
    )
    tokens = {
        "access_token": "acc",
        "refresh_token": "ref",
        "token_type": "bearer",
        "expires_in": 900,
    }

    async def _override_db():
        yield mock_db

    async def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "email": user.email,
                "name": user.name,
                "provider": "google",
                "provider_account_id": "123",
            }
            unauth = await client.post("/api/auth/verify", json=payload)
            assert unauth.status_code == 401

            with (
                patch("app.api.auth.get_or_create_oauth_user", new=AsyncMock(return_value=(user, tokens))),
                patch("app.api.auth.build_user_response", new=AsyncMock(return_value=user_resp)),
            ):
                ok = await client.post(
                    "/api/auth/verify",
                    json=payload,
                    headers={"X-Internal-Auth-Secret": "top-secret"},
                )
            assert ok.status_code == 200
            assert ok.json()["tokens"]["access_token"] == "acc"

            with patch("app.api.auth.refresh_access_tokens", new=AsyncMock(return_value=TokenResponse(**tokens))):
                ref = await client.post("/api/auth/refresh", json={"refresh_token": "ref"})
            assert ref.status_code == 200
            assert ref.json()["refresh_token"] == "ref"

            with patch("app.api.auth.build_user_response", new=AsyncMock(return_value=user_resp)):
                me = await client.get("/api/auth/me")
            assert me.status_code == 200
            assert me.json()["email"] == user.email
    finally:
        app.dependency_overrides.clear()
