"""Unit tests for app.api.ats_checker."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.main import app
from app.security.rate_limiter import limiter
from tests.conftest import make_ats_check_result


@pytest.mark.asyncio
async def test_analyze_cv_validation_and_success(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)
    expected = make_ats_check_result()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        bad_mime = await client.post(
            "/api/ats-checker/analyze",
            files={"file": ("cv.txt", b"hi", "text/plain")},
        )
        assert bad_mime.status_code == 400

        empty = await client.post(
            "/api/ats-checker/analyze",
            files={"file": ("cv.pdf", b"", "application/pdf")},
        )
        assert empty.status_code == 400

        fake_pdf = await client.post(
            "/api/ats-checker/analyze",
            files={"file": ("cv.pdf", b"not-a-pdf", "application/pdf")},
        )
        assert fake_pdf.status_code == 400
        assert "Invalid file content" in fake_pdf.json()["detail"]

        monkeypatch.setattr("app.api.ats_checker.MAX_FILE_SIZE", 10)
        too_big = await client.post(
            "/api/ats-checker/analyze",
            files={"file": ("cv.pdf", b"%PDF-" + b"x" * 20, "application/pdf")},
        )
        assert too_big.status_code == 413

        monkeypatch.setattr("app.api.ats_checker.MAX_FILE_SIZE", 10 * 1024 * 1024)
        with patch("app.api.ats_checker.analyze_cv_pdf", new=AsyncMock(return_value=expected)) as mock_svc:
            ok = await client.post(
                "/api/ats-checker/analyze",
                files={"file": ("cv.pdf", b"%PDF-1.4 content", "application/pdf")},
                data={
                    "target_role": "Backend Engineer",
                    "company_name": "<b>Acme</b>",
                    "job_description": "Build <b>Python</b> APIs.",
                },
            )
        assert ok.status_code == 200
        assert ok.json()["overall_score"] == expected.overall_score
        mock_svc.assert_awaited_once_with(
            b"%PDF-1.4 content",
            target_role="Backend Engineer",
            company_name="Acme",
            job_description="Build Python APIs.",
        )
