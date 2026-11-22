"""Unit tests for app.services.ats_checker_service."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import GenerationError
from app.services import ats_checker_service
from tests.conftest import make_ats_check_result


@pytest.mark.asyncio
async def test_analyze_cv_pdf_success_and_error():
    expected = make_ats_check_result()
    with patch(
        "app.services.ats_checker_service.check_cv_ats",
        new=AsyncMock(return_value={"result": expected}),
    ) as mock_check:
        res = await ats_checker_service.analyze_cv_pdf(
            b"%PDF-1.4",
            target_role="Backend",
            company_name="Acme",
            job_description="Python & FastAPI role",
        )
    assert res is expected
    mock_check.assert_awaited_once_with(
        b"%PDF-1.4",
        target_role="Backend",
        company_name="Acme",
        job_description="Python & FastAPI role",
    )

    with patch(
        "app.services.ats_checker_service.check_cv_ats",
        new=AsyncMock(return_value={"error": "parse error"}),
    ):
        with pytest.raises(GenerationError, match="parse error"):
            await ats_checker_service.analyze_cv_pdf(b"%PDF-1.4")
