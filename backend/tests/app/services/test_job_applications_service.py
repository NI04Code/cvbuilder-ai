"""Unit tests for app.services.job_applications_service."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.schemas.job_applications import ApplicationCreateRequest, ApplicationUpdateRequest
from app.services import job_applications_service
from tests.conftest import make_job_application, make_user


@pytest.mark.asyncio
async def test_job_applications_service_crud_and_stats(mock_db):
    user = make_user()
    row = make_job_application(user_id=user.id, status="applied")

    create_req = ApplicationCreateRequest(
        company_name="Acme Corp",
        role_title="Backend Engineer",
        job_url="https://acme.example.com/jobs/1",
        status="applied",
    )
    with patch(
        "app.services.job_applications_service.job_applications_repo.create_application",
        new=AsyncMock(side_effect=lambda db, rec: rec),
    ):
        created = await job_applications_service.create_user_application(
            mock_db, user.id, create_req
        )
    assert created.user_id == user.id
    assert created.company_name == "Acme Corp"
    assert created.status == "applied"

    with patch(
        "app.services.job_applications_service.job_applications_repo.list_applications",
        new=AsyncMock(return_value=[row]),
    ) as mock_list:
        items = await job_applications_service.list_user_applications(
            mock_db, user.id, status_filter="applied", search_query="Acme", limit=25, offset=0
        )
    assert items == [row]
    mock_list.assert_awaited_once_with(
        mock_db, user.id, status_filter="applied", search_query="Acme", limit=25, offset=0
    )

    with patch(
        "app.services.job_applications_service.job_applications_repo.count_by_status",
        new=AsyncMock(return_value={"saved": 2, "applied": 3, "offer": 1}),
    ):
        stats = await job_applications_service.get_user_application_stats(mock_db, user.id)
    assert stats.total == 6
    assert stats.saved == 2
    assert stats.applied == 3
    assert stats.offer == 1
    assert stats.interviewing == 0

    with patch(
        "app.services.job_applications_service.job_applications_repo.get_owned_application",
        new=AsyncMock(return_value=row),
    ):
        fetched = await job_applications_service.get_user_application(mock_db, row.id, user.id)
    assert fetched is row

    with patch(
        "app.services.job_applications_service.job_applications_repo.get_owned_application",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(NotFoundError, match="Application not found"):
            await job_applications_service.get_user_application(mock_db, uuid.uuid4(), user.id)

    upd_req = ApplicationUpdateRequest(status="interviewing", notes="Phone screen scheduled")
    with (
        patch(
            "app.services.job_applications_service.job_applications_repo.get_owned_application",
            new=AsyncMock(return_value=row),
        ),
        patch(
            "app.services.job_applications_service.job_applications_repo.update_application",
            new=AsyncMock(side_effect=lambda db, rec: rec),
        ),
    ):
        updated = await job_applications_service.update_user_application(
            mock_db, row.id, user.id, upd_req
        )
    assert updated.status == "interviewing"
    assert updated.notes == "Phone screen scheduled"

    with (
        patch(
            "app.services.job_applications_service.job_applications_repo.get_owned_application",
            new=AsyncMock(return_value=row),
        ),
        patch(
            "app.services.job_applications_service.job_applications_repo.delete_application",
            new=AsyncMock(),
        ) as mock_del,
    ):
        await job_applications_service.delete_user_application(mock_db, row.id, user.id)
    mock_del.assert_awaited_once_with(mock_db, row)
