"""Unit tests for app.services.auth_service."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import ConflictError, UnauthorizedError
from app.schemas.user import LoginRequest, OAuthVerifyRequest, RegisterRequest
from app.security.encryption import decrypt_secret
from app.security.jwt import create_token_pair
from app.security.password import hash_password
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


@pytest.mark.asyncio
async def test_register_and_authenticate_manual_user(mock_db):
    new_user = make_user(email="manual@example.com", name="Manual User")
    reg_req = RegisterRequest(
        name="Manual User",
        email="manual@example.com",
        password="Password1",
    )

    with (
        patch("app.services.auth_service.user_repo.get_user_by_email", new=AsyncMock(return_value=None)),
        patch("app.services.auth_service.user_repo.create_user", new=AsyncMock(return_value=new_user)) as mock_create,
        patch("app.services.auth_service.user_repo.flush_changes", new=AsyncMock()),
    ):
        created_user, tokens = await auth_service.register_manual_user(mock_db, reg_req)
    assert created_user is new_user
    assert tokens["access_token"]
    assert mock_create.call_args.kwargs["hashed_password"] != "Password1"

    # Duplicate email -> ConflictError
    with patch("app.services.auth_service.user_repo.get_user_by_email", new=AsyncMock(return_value=new_user)):
        with pytest.raises(ConflictError, match="already exists"):
            await auth_service.register_manual_user(mock_db, reg_req)

    # Authenticate manual user
    pw_user = make_user(
        email="manual@example.com",
        hashed_password=hash_password("Password1"),
        is_active=True,
    )
    login_req = LoginRequest(email="manual@example.com", password="Password1")

    with patch("app.services.auth_service.user_repo.get_user_by_email", new=AsyncMock(return_value=pw_user)):
        authed, auth_tokens = await auth_service.authenticate_manual_user(mock_db, login_req)
    assert authed is pw_user
    assert auth_tokens["refresh_token"]

    # Wrong password -> UnauthorizedError
    bad_login = LoginRequest(email="manual@example.com", password="WrongPassword1")
    with patch("app.services.auth_service.user_repo.get_user_by_email", new=AsyncMock(return_value=pw_user)):
        with pytest.raises(UnauthorizedError, match="Invalid email or password"):
            await auth_service.authenticate_manual_user(mock_db, bad_login)

    # Missing user -> UnauthorizedError
    with patch("app.services.auth_service.user_repo.get_user_by_email", new=AsyncMock(return_value=None)):
        with pytest.raises(UnauthorizedError, match="Invalid email or password"):
            await auth_service.authenticate_manual_user(mock_db, login_req)

    # OAuth-only user (no password) -> UnauthorizedError
    oauth_only = make_user(email="oauth@example.com", hashed_password=None)
    with patch("app.services.auth_service.user_repo.get_user_by_email", new=AsyncMock(return_value=oauth_only)):
        with pytest.raises(UnauthorizedError, match="Invalid email or password"):
            await auth_service.authenticate_manual_user(mock_db, login_req)

    # Inactive user -> UnauthorizedError
    inactive_pw = make_user(
        email="manual@example.com",
        hashed_password=hash_password("Password1"),
        is_active=False,
    )
    with patch("app.services.auth_service.user_repo.get_user_by_email", new=AsyncMock(return_value=inactive_pw)):
        with pytest.raises(UnauthorizedError, match="deactivated"):
            await auth_service.authenticate_manual_user(mock_db, login_req)
