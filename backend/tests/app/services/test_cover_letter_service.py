"""Unit tests for app.services.cover_letter_service."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import GenerationError
from app.schemas.cover_letter import CoverLetterContent, CoverLetterGenerateRequest
from app.services import cover_letter_service
from tests.conftest import (
    make_generated_cover_letter,
    make_profile,
    make_profile_response,
    make_user,
)


@pytest.mark.asyncio
async def test_generate_tailored_cover_letter_success_and_errors(mock_db, tmp_path: Path):
    user = make_user()
    profile = make_profile(user_id=user.id)
    profile_resp = make_profile_response(user.id)
    content = CoverLetterContent(cover_letter_text="Dear Hiring Team,\n\n" + "Body text. " * 10)
    req = CoverLetterGenerateRequest(job_description="A" * 60, job_title="Backend Eng")

    with (
        patch(
            "app.services.cover_letter_service.get_user_profile_for_generation",
            new=AsyncMock(return_value=(profile, profile_resp)),
        ),
        patch(
            "app.services.cover_letter_service.process_cover_letter_generation",
            new=AsyncMock(return_value={"cover_letter": content, "resolved_company": "Acme"}),
        ),
        patch(
            "app.services.cover_letter_service.get_generated_document_path",
            return_value=tmp_path / "cl.pdf",
        ),
        patch("app.services.cover_letter_service.generate_cover_letter_pdf") as mock_pdf,
        patch(
            "app.services.cover_letter_service.document_repo.save_document",
            new=AsyncMock(side_effect=lambda db, rec: rec),
        ),
    ):
        created = await cover_letter_service.generate_tailored_cover_letter(mock_db, user, req)

    assert created.company_name == "Acme"
    assert created.cover_letter_text == content.cover_letter_text
    mock_pdf.assert_called_once()

    with (
        patch(
            "app.services.cover_letter_service.get_user_profile_for_generation",
            new=AsyncMock(return_value=(profile, profile_resp)),
        ),
        patch(
            "app.services.cover_letter_service.process_cover_letter_generation",
            new=AsyncMock(return_value={"error": "cl failed"}),
        ),
    ):
        with pytest.raises(GenerationError, match="cl failed"):
            await cover_letter_service.generate_tailored_cover_letter(mock_db, user, req)

    with (
        patch(
            "app.services.cover_letter_service.get_user_profile_for_generation",
            new=AsyncMock(return_value=(profile, profile_resp)),
        ),
        patch(
            "app.services.cover_letter_service.process_cover_letter_generation",
            new=AsyncMock(return_value={"cover_letter": content}),
        ),
        patch(
            "app.services.cover_letter_service.generate_cover_letter_pdf",
            side_effect=RuntimeError("pdf err"),
        ),
    ):
        with pytest.raises(GenerationError, match="Failed to generate cover letter PDF"):
            await cover_letter_service.generate_tailored_cover_letter(mock_db, user, req)


@pytest.mark.asyncio
async def test_cover_letter_service_crud_delegates(mock_db):
    user = make_user()
    cl = make_generated_cover_letter(user_id=user.id)

    with patch("app.services.cover_letter_service.document_repo.list_by_user", new=AsyncMock(return_value=[cl])):
        assert await cover_letter_service.list_user_cover_letters(mock_db, user.id, limit=10, offset=0) == [cl]

    with patch("app.services.cover_letter_service.get_owned_document", new=AsyncMock(return_value=cl)):
        assert await cover_letter_service.get_user_cover_letter(mock_db, cl.id, user.id) is cl

    with patch("app.services.cover_letter_service.get_download_file_info", new=AsyncMock(return_value=("/cl.pdf", "cl.pdf"))):
        assert await cover_letter_service.get_cover_letter_download_info(mock_db, cl.id, user) == ("/cl.pdf", "cl.pdf")

    with patch("app.services.cover_letter_service.delete_owned_document", new=AsyncMock()) as mock_del:
        await cover_letter_service.delete_user_cover_letter(mock_db, cl.id, user.id)
    mock_del.assert_awaited_once()
