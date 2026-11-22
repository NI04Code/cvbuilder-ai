"""Cold email generation, retrieval, and deletion business logic."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cold_email_agent import process_cold_email_generation
from app.core.exceptions import GenerationError
from app.database import document_repo
from app.models.cold_email import GeneratedColdEmail
from app.models.user import User
from app.schemas.cold_email import ColdEmailGenerateRequest
from app.services.document_service import (
    delete_owned_document,
    get_owned_document,
    get_user_profile_for_generation,
)


async def generate_tailored_cold_email(
    db: AsyncSession,
    user: User,
    data: ColdEmailGenerateRequest,
) -> GeneratedColdEmail:
    """Generate a concise recruiter cold email and persist it."""
    profile, profile_response = await get_user_profile_for_generation(db, user.id)

    result = await process_cold_email_generation(
        profile_response, data, user_name=user.name
    )
    if result.get("error") or not result.get("cold_email"):
        raise GenerationError(
            result.get("error") or "Failed to generate cold email."
        )

    cold_email = result["cold_email"]
    resolved_company = data.company_name or result.get("resolved_company")

    record = GeneratedColdEmail(
        id=uuid.uuid4(),
        user_id=user.id,
        profile_id=profile.id,
        job_description=data.job_description,
        job_title=data.job_title,
        company_name=resolved_company,
        recruiter_name=data.recruiter_name,
        subject=cold_email.subject,
        email_body=cold_email.email_body,
        created_at=datetime.now(timezone.utc),
    )
    return await document_repo.save_document(db, record)


async def list_user_cold_emails(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[GeneratedColdEmail]:
    """Return a paginated list of generated cold emails owned by the user."""
    return await document_repo.list_by_user(
        db, GeneratedColdEmail, user_id, limit=limit, offset=offset
    )


async def get_user_cold_email(
    db: AsyncSession,
    cold_email_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GeneratedColdEmail:
    """Fetch a single generated cold email owned by the user."""
    return await get_owned_document(
        db,
        GeneratedColdEmail,
        cold_email_id,
        user_id,
        not_found_detail="Cold email not found",
    )


async def delete_user_cold_email(
    db: AsyncSession,
    cold_email_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete an owned cold email record."""
    await delete_owned_document(
        db,
        GeneratedColdEmail,
        cold_email_id,
        user_id,
        not_found_detail="Cold email not found",
    )
