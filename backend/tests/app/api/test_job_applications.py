"""Unit tests for app.api.job_applications."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.database import get_db
from app.main import app
from app.schemas.job_applications import ApplicationStatsResponse
from app.security.jwt import get_current_user
from tests.conftest import make_job_application, make_user


@pytest.mark.asyncio
async def test_job_application_endpoints(mock_db):
    user = make_user()
    row = make_job_application(user_id=user.id)

    async def _override_db():
        yield mock_db

    async def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch(
                "app.api.job_applications.create_user_application",
                new=AsyncMock(return_value=row),
            ):
                r_create = await client.post(
                    "/api/job-applications",
                    json={
                        "company_name": "Acme Corp",
                        "role_title": "Backend Engineer",
                        "job_url": "https://acme.example.com/jobs/1",
                        "status": "applied",
                    },
                )
            assert r_create.status_code == 201
            assert r_create.json()["id"] == str(row.id)
            assert r_create.json()["company_name"] == row.company_name

            with patch(
                "app.api.job_applications.list_user_applications",
                new=AsyncMock(return_value=[row]),
            ) as mock_list:
                r_list = await client.get(
                    "/api/job-applications?status=applied&q=Acme&limit=20&offset=0"
                )
            assert r_list.status_code == 200
            assert len(r_list.json()) == 1
            mock_list.assert_awaited_once_with(
                mock_db,
                user.id,
                status_filter="applied",
                search_query="Acme",
                limit=20,
                offset=0,
            )

            with patch(
                "app.api.job_applications.get_user_application_stats",
                new=AsyncMock(return_value=ApplicationStatsResponse(total=1, applied=1)),
            ):
                r_stats = await client.get("/api/job-applications/stats")
            assert r_stats.status_code == 200
            assert r_stats.json()["total"] == 1
            assert r_stats.json()["applied"] == 1

            with patch(
                "app.api.job_applications.get_user_application",
                new=AsyncMock(return_value=row),
            ):
                r_get = await client.get(f"/api/job-applications/{row.id}")
            assert r_get.status_code == 200

            with patch(
                "app.api.job_applications.update_user_application",
                new=AsyncMock(return_value=row),
            ):
                r_patch = await client.patch(
                    f"/api/job-applications/{row.id}",
                    json={"status": "interviewing"},
                )
            assert r_patch.status_code == 200

            with patch(
                "app.api.job_applications.delete_user_application",
                new=AsyncMock(),
            ):
                r_del = await client.delete(f"/api/job-applications/{row.id}")
            assert r_del.status_code == 204
    finally:
        app.dependency_overrides.clear()
