"""Unit tests for app.api.cover_letter."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.database import get_db
from app.main import app
from app.security.jwt import get_current_user
from tests.conftest import make_generated_cover_letter, make_user


@pytest.mark.asyncio
async def test_cover_letter_endpoints(mock_db, tmp_path: Path):
    user = make_user()
    cl = make_generated_cover_letter(user_id=user.id)
    pdf_path = tmp_path / "cover-letter-Acme-Alex.pdf"
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
            with patch("app.api.cover_letter.generate_tailored_cover_letter", new=AsyncMock(return_value=cl)):
                r_gen = await client.post("/api/cover-letters/generate", json={"job_description": "A" * 60})
            assert r_gen.status_code == 200
            assert r_gen.json()["id"] == str(cl.id)

            with patch("app.api.cover_letter.list_user_cover_letters", new=AsyncMock(return_value=[cl])) as mock_list:
                r_list = await client.get("/api/cover-letters/history?limit=20&offset=0")
            assert r_list.status_code == 200
            assert len(r_list.json()) == 1
            mock_list.assert_awaited_once_with(mock_db, user.id, limit=20, offset=0)

            with patch("app.api.cover_letter.get_user_cover_letter", new=AsyncMock(return_value=cl)):
                r_get = await client.get(f"/api/cover-letters/{cl.id}")
            assert r_get.status_code == 200

            with patch(
                "app.api.cover_letter.get_cover_letter_download_info",
                new=AsyncMock(return_value=(str(pdf_path), "cover-letter-Acme-Alex.pdf")),
            ):
                r_dl = await client.get(f"/api/cover-letters/{cl.id}/download")
            assert r_dl.status_code == 200
            assert "cover-letter-Acme-Alex.pdf" in r_dl.headers["content-disposition"]

            with patch("app.api.cover_letter.delete_user_cover_letter", new=AsyncMock()):
                r_del = await client.delete(f"/api/cover-letters/{cl.id}")
            assert r_del.status_code == 204
    finally:
        app.dependency_overrides.clear()
