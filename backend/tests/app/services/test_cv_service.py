"""Unit tests for app.services.cv_service."""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import GenerationError
from app.schemas.cv import CVGenerateRequest
from app.services import cv_service
from tests.conftest import (
    make_generated_cv,
    make_profile,
    make_profile_response,
    make_tailored_cv,
    make_user,
)


@pytest.mark.asyncio
async def test_generate_tailored_cv_success_and_errors(mock_db, tmp_path: Path):
    user = make_user()
    profile = make_profile(user_id=user.id)
    profile_resp = make_profile_response(user.id)
    tailored = make_tailored_cv()
    req = CVGenerateRequest(job_description="A" * 60, job_title="SWE")

    with (
        patch(
            "app.services.cv_service.get_user_profile_for_generation",
            new=AsyncMock(return_value=(profile, profile_resp)),
        ),
        patch(
            "app.services.cv_service.process_cv_generation",
            new=AsyncMock(return_value={"tailored_cv": tailored, "resolved_company": "Acme"}),
        ),
        patch(
            "app.services.cv_service.get_generated_document_path",
            return_value=tmp_path / "cv.pdf",
        ),
        patch("app.services.cv_service.generate_cv_pdf") as mock_pdf,
        patch(
            "app.services.cv_service.document_repo.save_document",
            new=AsyncMock(side_effect=lambda db, rec: rec),
        ),
    ):
        created = await cv_service.generate_tailored_cv(mock_db, user, req)

    assert created.company_name == "Acme"
    assert created.ats_score == tailored.ats_score
    mock_pdf.assert_called_once()

    with (
        patch(
            "app.services.cv_service.get_user_profile_for_generation",
            new=AsyncMock(return_value=(profile, profile_resp)),
        ),
        patch(
            "app.services.cv_service.process_cv_generation",
            new=AsyncMock(return_value={"error": "agent failed"}),
        ),
    ):
        with pytest.raises(GenerationError, match="agent failed"):
            await cv_service.generate_tailored_cv(mock_db, user, req)

    with (
        patch(
            "app.services.cv_service.get_user_profile_for_generation",
            new=AsyncMock(return_value=(profile, profile_resp)),
        ),
        patch(
            "app.services.cv_service.process_cv_generation",
            new=AsyncMock(return_value={"tailored_cv": tailored}),
        ),
        patch("app.services.cv_service.generate_cv_pdf", side_effect=RuntimeError("pdf err")),
    ):
        with pytest.raises(GenerationError, match="Failed to generate PDF"):
            await cv_service.generate_tailored_cv(mock_db, user, req)


@pytest.mark.asyncio
async def test_cv_service_crud_delegates(mock_db):
    user = make_user()
    cv = make_generated_cv(user_id=user.id)

    with patch("app.services.cv_service.document_repo.list_by_user", new=AsyncMock(return_value=[cv])):
        assert await cv_service.list_user_cvs(mock_db, user.id, limit=10, offset=0) == [cv]

    with patch("app.services.cv_service.get_owned_document", new=AsyncMock(return_value=cv)):
        assert await cv_service.get_user_cv(mock_db, cv.id, user.id) is cv

    with patch("app.services.cv_service.get_download_file_info", new=AsyncMock(return_value=("/p.pdf", "cv.pdf"))):
        assert await cv_service.get_cv_download_info(mock_db, cv.id, user) == ("/p.pdf", "cv.pdf")

    with patch("app.services.cv_service.delete_owned_document", new=AsyncMock()) as mock_del:
        await cv_service.delete_user_cv(mock_db, cv.id, user.id)
    mock_del.assert_awaited_once()
