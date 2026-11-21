"""Unit tests for app.database.profile_repo."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.database import profile_repo
from tests.conftest import make_profile, make_scalar_result


@pytest.mark.asyncio
async def test_has_profile(mock_db):
    uid = uuid.uuid4()
    mock_db.execute = AsyncMock(return_value=make_scalar_result(uuid.uuid4()))
    assert await profile_repo.has_profile(mock_db, uid) is True

    mock_db.execute = AsyncMock(return_value=make_scalar_result(None))
    assert await profile_repo.has_profile(mock_db, uid) is False


@pytest.mark.asyncio
async def test_get_by_user_id_and_save_profile(mock_db):
    profile = make_profile()
    mock_db.execute = AsyncMock(return_value=make_scalar_result(profile))
    assert await profile_repo.get_by_user_id(mock_db, profile.user_id) is profile

    saved_existing = await profile_repo.save_profile(mock_db, profile, is_new=False)
    assert saved_existing is profile
    mock_db.add.assert_not_called()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(profile)

    mock_db.reset_mock()
    saved_new = await profile_repo.save_profile(mock_db, profile, is_new=True)
    assert saved_new is profile
    mock_db.add.assert_called_once_with(profile)
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(profile)
