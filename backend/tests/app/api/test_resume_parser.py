"""Unit tests for app.api.resume_parser."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.database import get_db
from app.main import app
from app.security.jwt import get_current_user
from tests.conftest import make_profile, make_user


@pytest.mark.asyncio
async def test_upload_resume_endpoint(mock_db):
    user = make_user()
    profile = make_profile(user_id=user.id)

    async def _override_db():
        yield mock_db

    async def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    try:
        with patch("app.api.resume_parser.upload_and_parse_resume", new=AsyncMock(return_value=profile)):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/resume/upload",
                    files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
                )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(profile.id)
    finally:
        app.dependency_overrides.clear()
