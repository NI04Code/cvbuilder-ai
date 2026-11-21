"""Unit tests for app.main (lifespan, health_check, readiness_check)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.database import get_db
from app.main import app, health_check, lifespan, readiness_check


@pytest.mark.asyncio
async def test_lifespan_validates_secrets_and_creates_dirs(tmp_path, monkeypatch):
    from app.core import Settings, settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "generated_dir", str(tmp_path / "generated"))
    with patch.object(Settings, "validate_production_secrets") as mock_validate:
        async with lifespan(app):
            pass
    mock_validate.assert_called_once()
    assert (tmp_path / "uploads").is_dir()
    assert (tmp_path / "generated").is_dir()


@pytest.mark.asyncio
async def test_health_check():
    res = await health_check()
    assert res == {"status": "healthy", "service": "cvbuilder-ai-api"}


@pytest.mark.asyncio
async def test_readiness_check_success_and_failure(mock_db):
    mock_db.execute = AsyncMock(return_value=MagicMock())
    ok = await readiness_check(db=mock_db)
    assert ok == {"status": "ready", "service": "cvbuilder-ai-api"}

    failing_db = AsyncMock()
    failing_db.execute = AsyncMock(side_effect=RuntimeError("db down"))

    async def _override_fail_db():
        yield failing_db

    app.dependency_overrides[get_db] = _override_fail_db
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json() == {"status": "unavailable"}
    finally:
        app.dependency_overrides.clear()
