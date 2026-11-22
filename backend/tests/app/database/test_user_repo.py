"""Unit tests for app.database.user_repo."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.database import user_repo
from tests.conftest import make_oauth_account, make_scalar_result, make_user


@pytest.mark.asyncio
async def test_get_user_by_id_and_email(mock_db):
    user = make_user()
    mock_db.execute = AsyncMock(return_value=make_scalar_result(user))
    assert await user_repo.get_user_by_id(mock_db, user.id) is user

    mock_db.execute = AsyncMock(return_value=make_scalar_result(user))
    assert await user_repo.get_user_by_email(mock_db, user.email) is user


@pytest.mark.asyncio
async def test_create_user_and_flush(mock_db):
    user = await user_repo.create_user(
        mock_db,
        email="new@example.com",
        name="New User",
        avatar_url=None,
        hashed_password="$2b$12$hashedvalue",
    )
    assert user.email == "new@example.com"
    assert user.is_active is True
    assert user.hashed_password == "$2b$12$hashedvalue"
    mock_db.add.assert_called_once_with(user)
    mock_db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_and_create_oauth_account_and_flush_changes(mock_db):
    uid = uuid.uuid4()
    acct = make_oauth_account(uid)
    mock_db.execute = AsyncMock(return_value=make_scalar_result(acct))
    found = await user_repo.get_oauth_account(
        mock_db, user_id=uid, provider="google", provider_account_id="acct-123"
    )
    assert found is acct

    created = await user_repo.create_oauth_account(
        mock_db,
        user_id=uid,
        provider="github",
        provider_account_id="gh-1",
        access_token="enc:abc",
    )
    assert created.provider == "github"
    assert created.access_token == "enc:abc"
    mock_db.add.assert_called_once_with(created)

    await user_repo.flush_changes(mock_db)
    mock_db.flush.assert_awaited_once()
