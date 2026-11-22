"""Unit tests for app.services.cold_email_service."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import GenerationError
from app.schemas.cold_email import ColdEmailContent, ColdEmailGenerateRequest
from app.services import cold_email_service
from tests.conftest import (
    make_generated_cold_email,
    make_profile,
    make_profile_response,
    make_user,
)


@pytest.mark.asyncio
async def test_generate_tailored_cold_email_success_and_errors(mock_db):
    user = make_user()
    profile = make_profile(user_id=user.id)
    profile_resp = make_profile_response(user.id)
    content = ColdEmailContent(
        subject="Cut API latency 35% — Backend Engineer",
        email_body="Hi Sarah,\n\n" + "Hook and impact details. " * 4,
    )
    req = ColdEmailGenerateRequest(
        job_description="A" * 60,
        job_title="Backend Eng",
        recruiter_name="Sarah Jenkins",
    )

    with (
        patch(
            "app.services.cold_email_service.get_user_profile_for_generation",
            new=AsyncMock(return_value=(profile, profile_resp)),
        ),
        patch(
            "app.services.cold_email_service.process_cold_email_generation",
            new=AsyncMock(return_value={"cold_email": content, "resolved_company": "Acme"}),
        ),
        patch(
            "app.services.cold_email_service.document_repo.save_document",
            new=AsyncMock(side_effect=lambda db, rec: rec),
        ),
    ):
        created = await cold_email_service.generate_tailored_cold_email(mock_db, user, req)

    assert created.company_name == "Acme"
    assert created.recruiter_name == "Sarah Jenkins"
    assert created.subject == content.subject
    assert created.email_body == content.email_body

    with (
        patch(
            "app.services.cold_email_service.get_user_profile_for_generation",
            new=AsyncMock(return_value=(profile, profile_resp)),
        ),
        patch(
            "app.services.cold_email_service.process_cold_email_generation",
            new=AsyncMock(return_value={"error": "agent failed"}),
        ),
    ):
        with pytest.raises(GenerationError, match="agent failed"):
            await cold_email_service.generate_tailored_cold_email(mock_db, user, req)


@pytest.mark.asyncio
async def test_cold_email_service_crud_delegates(mock_db):
    user = make_user()
    email = make_generated_cold_email(user_id=user.id)

    with patch(
        "app.services.cold_email_service.document_repo.list_by_user",
        new=AsyncMock(return_value=[email]),
    ):
        assert await cold_email_service.list_user_cold_emails(mock_db, user.id, limit=10, offset=0) == [email]

    with patch(
        "app.services.cold_email_service.get_owned_document",
        new=AsyncMock(return_value=email),
    ):
        assert await cold_email_service.get_user_cold_email(mock_db, email.id, user.id) is email

    with patch(
        "app.services.cold_email_service.delete_owned_document",
        new=AsyncMock(),
    ) as mock_del:
        await cold_email_service.delete_user_cold_email(mock_db, email.id, user.id)
    mock_del.assert_awaited_once()
