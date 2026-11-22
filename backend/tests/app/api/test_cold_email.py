"""Unit tests for app.api.cold_email."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.database import get_db
from app.main import app
from app.security.jwt import get_current_user
from tests.conftest import make_generated_cold_email, make_user


@pytest.mark.asyncio
async def test_cold_email_endpoints(mock_db):
    user = make_user()
    email = make_generated_cold_email(user_id=user.id)

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
                "app.api.cold_email.generate_tailored_cold_email",
                new=AsyncMock(return_value=email),
            ):
                r_gen = await client.post(
                    "/api/cold-emails/generate",
                    json={
                        "job_description": "A" * 60,
                        "job_title": "Backend Engineer",
                        "company_name": "Acme Corp",
                        "recruiter_name": "Sarah Jenkins",
                    },
                )
            assert r_gen.status_code == 200
            assert r_gen.json()["id"] == str(email.id)
            assert r_gen.json()["recruiter_name"] == "Sarah Jenkins"
            assert r_gen.json()["subject"] == email.subject

            with patch(
                "app.api.cold_email.list_user_cold_emails",
                new=AsyncMock(return_value=[email]),
            ) as mock_list:
                r_list = await client.get("/api/cold-emails/history?limit=20&offset=0")
            assert r_list.status_code == 200
            assert len(r_list.json()) == 1
            mock_list.assert_awaited_once_with(mock_db, user.id, limit=20, offset=0)

            with patch(
                "app.api.cold_email.get_user_cold_email",
                new=AsyncMock(return_value=email),
            ):
                r_get = await client.get(f"/api/cold-emails/{email.id}")
            assert r_get.status_code == 200

            with patch(
                "app.api.cold_email.delete_user_cold_email",
                new=AsyncMock(),
            ):
                r_del = await client.delete(f"/api/cold-emails/{email.id}")
            assert r_del.status_code == 204
    finally:
        app.dependency_overrides.clear()
