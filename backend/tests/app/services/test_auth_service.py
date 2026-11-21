"""Unit tests for app.services.auth_service."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import UnauthorizedError
from app.schemas.user import OAuthVerifyRequest
from app.security.encryption import decrypt_secret
from app.security.jwt import create_token_pair
from app.services import auth_service
from tests.conftest import make_oauth_account, make_user


@pytest.mark.asyncio
async def test_get_or_create_oauth_user_new_and_existing(mock_db):
    user = make_user(avatar_url=None, name="Old Name")
    req = OAuthVerifyRequest(
        email=user.email,
        name="New Name",
        provider="google",
        provider_account_id="g-1",
        avatar_url="https://example.com/pic.png",
        access_token="oauth-secret-1",
    )

    with (
        patch("app.services.auth_service.user_repo.get_user_by_email", new=AsyncMock(return_value=None)),
        patch("app.services.auth_service.user_repo.create_user", new=AsyncMock(return_value=user)) as mock_create_user,
        patch("app.services.auth_service.user_repo.get_oauth_account", new=AsyncMock(return_value=None)),
        patch("app.services.auth_service.user_repo.create_oauth_account", new=AsyncMock()) as mock_create_oauth,
        patch("app.services.auth_service.user_repo.flush_changes", new=AsyncMock()) as mock_flush,
    ):
        returned_user, tokens = await auth_service.get_or_create_oauth_user(mock_db, req)

    assert returned_user is user
    assert user.name == "New Name"
    assert user.avatar_url == "https://example.com/pic.png"
    assert tokens["access_token"]
    mock_create_user.assert_awaited_once()
    stored_token = mock_create_oauth.call_args.kwargs["access_token"]
    assert stored_token.startswith("enc:")
    assert decrypt_secret(stored_token) == "oauth-secret-1"
    mock_flush.assert_awaited_once()

    existing_oauth = make_oauth_account(user.id, access_token="old")
    with (
        patch("app.services.auth_service.user_repo.get_user_by_email", new=AsyncMock(return_value=user)),
        patch("app.services.auth_service.user_repo.get_oauth_account", new=AsyncMock(return_value=existing_oauth)),
        patch("app.services.auth_service.user_repo.flush_changes", new=AsyncMock()),
    ):
        await auth_service.get_or_create_oauth_user(mock_db, req)
    assert existing_oauth.access_token.startswith("enc:")
    assert decrypt_secret(existing_oauth.access_token) == "oauth-secret-1"


@pytest.mark.asyncio
async def test_get_user_by_id_and_build_user_response(mock_db):
    user = make_user()
    with patch("app.services.auth_service.user_repo.get_user_by_id", new=AsyncMock(return_value=user)):
        assert await auth_service.get_user_by_id(mock_db, user.id) is user

    with patch("app.services.auth_service.profile_repo.has_profile", new=AsyncMock(return_value=True)):
        resp = await auth_service.build_user_response(mock_db, user)
    assert resp.id == user.id
    assert resp.has_profile is True


@pytest.mark.asyncio
async def test_refresh_access_tokens_paths(mock_db):
    user = make_user()
    pair = create_token_pair(str(user.id), user.email)

    with patch("app.services.auth_service.user_repo.get_user_by_id", new=AsyncMock(return_value=user)):
        refreshed = await auth_service.refresh_access_tokens(mock_db, pair["refresh_token"])
    assert refreshed.access_token
    assert refreshed.refresh_token

    # Access token rejected
    with pytest.raises(UnauthorizedError, match="refresh token required"):
        await auth_service.refresh_access_tokens(mock_db, pair["access_token"])

    # Missing sub
    with patch("app.services.auth_service.decode_token", return_value={"type": "refresh"}):
        with pytest.raises(UnauthorizedError, match="Invalid refresh token"):
            await auth_service.refresh_access_tokens(mock_db, "tok")

    # Bad UUID sub
    with patch("app.services.auth_service.decode_token", return_value={"type": "refresh", "sub": "not-uuid"}):
        with pytest.raises(UnauthorizedError, match="Invalid user identifier"):
            await auth_service.refresh_access_tokens(mock_db, "tok")

    # Inactive or missing user
    inactive = make_user(is_active=False)
    with (
        patch("app.services.auth_service.decode_token", return_value={"type": "refresh", "sub": str(uuid.uuid4())}),
        patch("app.services.auth_service.user_repo.get_user_by_id", new=AsyncMock(return_value=inactive)),
    ):
        with pytest.raises(UnauthorizedError, match="deactivated"):
            await auth_service.refresh_access_tokens(mock_db, "tok")
