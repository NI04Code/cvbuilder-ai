"""Unit tests for app.api.cv."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.exceptions import BadRequestError
from app.database import get_db
from app.main import app
from app.security.jwt import get_current_user
from tests.conftest import make_generated_cv, make_user


@pytest.mark.asyncio
async def test_cv_endpoints(mock_db, tmp_path: Path):
    user = make_user()
    cv = make_generated_cv(user_id=user.id)
    pdf_path = tmp_path / "cv-Acme-Alex.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 body")

    async def _override_db():
        yield mock_db

    async def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("app.api.cv.generate_tailored_cv", new=AsyncMock(return_value=cv)):
                r_gen = await client.post("/api/cv/generate", json={"job_description": "A" * 60})
            assert r_gen.status_code == 200
            assert r_gen.json()["id"] == str(cv.id)

            with patch("app.api.cv.generate_tailored_cv", new=AsyncMock(side_effect=BadRequestError("No profile"))):
                r_bad = await client.post("/api/cv/generate", json={"job_description": "A" * 60})
            assert r_bad.status_code == 400

            with patch("app.api.cv.list_user_cvs", new=AsyncMock(return_value=[cv])) as mock_list:
                r_list = await client.get("/api/cv/history?limit=10&offset=5")
            assert r_list.status_code == 200
            assert len(r_list.json()) == 1
            mock_list.assert_awaited_once_with(mock_db, user.id, limit=10, offset=5)

            with patch("app.api.cv.get_user_cv", new=AsyncMock(return_value=cv)):
                r_get = await client.get(f"/api/cv/{cv.id}")
            assert r_get.status_code == 200

            with patch("app.api.cv.get_cv_download_info", new=AsyncMock(return_value=(str(pdf_path), "cv-Acme-Alex.pdf"))):
                r_dl = await client.get(f"/api/cv/{cv.id}/download")
            assert r_dl.status_code == 200
            assert r_dl.headers["content-type"] == "application/pdf"
            assert "cv-Acme-Alex.pdf" in r_dl.headers["content-disposition"]

            with patch("app.api.cv.delete_user_cv", new=AsyncMock()):
                r_del = await client.delete(f"/api/cv/{cv.id}")
            assert r_del.status_code == 204
    finally:
        app.dependency_overrides.clear()
