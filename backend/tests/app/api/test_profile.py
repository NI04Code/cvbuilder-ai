"""Unit tests for app.api.profile."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.exceptions import NotFoundError
from app.database import get_db
from app.main import app
from app.security.jwt import get_current_user
from tests.conftest import make_profile, make_user


@pytest.mark.asyncio
async def test_get_and_update_profile_endpoints(mock_db):
    user = make_user()
    profile = make_profile(user_id=user.id)

    async def _override_db():
        yield mock_db

    async def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("app.api.profile.get_profile_by_user_id", new=AsyncMock(return_value=profile)):
                r_ok = await client.get("/api/profile/")
            assert r_ok.status_code == 200
            assert r_ok.json()["summary"] == profile.summary

            with patch("app.api.profile.get_profile_by_user_id", new=AsyncMock(side_effect=NotFoundError("Profile not found"))):
                r_404 = await client.get("/api/profile/")
            assert r_404.status_code == 404

            with patch("app.api.profile.upsert_profile", new=AsyncMock(return_value=profile)):
                r_put = await client.put("/api/profile/", json={"summary": "Updated"})
            assert r_put.status_code == 200
    finally:
        app.dependency_overrides.clear()
