"""Unit tests for app.services.profile_service."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.schemas.profile import ProfileUpdateRequest
from app.services import profile_service
from tests.conftest import make_profile


@pytest.mark.asyncio
async def test_get_profile_by_user_id(mock_db):
    profile = make_profile()
    with patch("app.services.profile_service.profile_repo.get_by_user_id", new=AsyncMock(return_value=profile)):
        assert await profile_service.get_profile_by_user_id(mock_db, profile.user_id) is profile

    with patch("app.services.profile_service.profile_repo.get_by_user_id", new=AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError):
            await profile_service.get_profile_by_user_id(mock_db, uuid.uuid4())


@pytest.mark.asyncio
async def test_upsert_profile_create_and_partial_update(mock_db):
    uid = uuid.uuid4()
    req_create = ProfileUpdateRequest(summary="Initial summary")

    with (
        patch("app.services.profile_service.profile_repo.get_by_user_id", new=AsyncMock(return_value=None)),
        patch(
            "app.services.profile_service.profile_repo.save_profile",
            new=AsyncMock(side_effect=lambda db, p, is_new=False: p),
        ) as mock_save,
    ):
        created = await profile_service.upsert_profile(mock_db, uid, req_create)
    assert created.summary == "Initial summary"
    assert mock_save.call_args.kwargs["is_new"] is True

    existing = make_profile(user_id=uid, summary="Old summary")
    req_update = ProfileUpdateRequest(summary="Updated summary")
    with (
        patch("app.services.profile_service.profile_repo.get_by_user_id", new=AsyncMock(return_value=existing)),
        patch(
            "app.services.profile_service.profile_repo.save_profile",
            new=AsyncMock(side_effect=lambda db, p, is_new=False: p),
        ) as mock_save2,
    ):
        updated = await profile_service.upsert_profile(mock_db, uid, req_update)
    assert updated.summary == "Updated summary"
    assert updated.work_experiences == existing.work_experiences
    assert mock_save2.call_args.kwargs["is_new"] is False
