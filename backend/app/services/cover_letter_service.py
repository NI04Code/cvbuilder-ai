"""Cover letter generation, retrieval, download, and deletion business logic."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cover_letter_agent import process_cover_letter_generation
from app.core.exceptions import GenerationError
from app.database import document_repo
from app.models.cover_letter import GeneratedCoverLetter
from app.models.user import User
from app.schemas.cover_letter import CoverLetterGenerateRequest
from app.services.document_service import (
    delete_owned_document,
    get_download_file_info,
    get_owned_document,
    get_user_profile_for_generation,
    resolve_candidate_identity,
)
from app.utils.file_handler import build_document_filename, get_generated_document_path
from app.utils.pdf_builder import generate_cover_letter_pdf


async def generate_tailored_cover_letter(
    db: AsyncSession,
    user: User,
    data: CoverLetterGenerateRequest,
) -> GeneratedCoverLetter:
    """Generate a single-page tailored cover letter, render its PDF, and persist the record."""
    profile, profile_response = await get_user_profile_for_generation(db, user.id)

    result = await process_cover_letter_generation(
        profile_response, data, user_name=user.name
    )
    if result.get("error") or not result.get("cover_letter"):
        raise GenerationError(
            result.get("error") or "Failed to generate cover letter."
        )

    cover_letter = result["cover_letter"]
    resolved_company = data.company_name or result.get("resolved_company")
    personal_info, user_name = resolve_candidate_identity(profile_response, user)

    cover_letter_id = uuid.uuid4()
    pdf_filename = build_document_filename(
        "cover-letter",
        resolved_company,
        user_name,
        unique_code=cover_letter_id.hex[:8],
    )
    pdf_path = get_generated_document_path(user.id, pdf_filename)

    try:
        await asyncio.to_thread(
            generate_cover_letter_pdf,
            cover_letter.cover_letter_text,
            personal_info,
            str(pdf_path),
            data.job_title,
            resolved_company,
        )
    except Exception as exc:
        raise GenerationError(f"Failed to generate cover letter PDF: {exc}") from exc

    record = GeneratedCoverLetter(
        id=cover_letter_id,
        user_id=user.id,
        profile_id=profile.id,
        job_description=data.job_description,
        job_title=data.job_title,
        company_name=resolved_company,
        cover_letter_text=cover_letter.cover_letter_text,
        pdf_file_path=str(pdf_path),
        created_at=datetime.now(timezone.utc),
    )
    return await document_repo.save_document(db, record)


async def list_user_cover_letters(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[GeneratedCoverLetter]:
    """Return a paginated list of generated cover letters owned by the user."""
    return await document_repo.list_by_user(
        db, GeneratedCoverLetter, user_id, limit=limit, offset=offset
    )


async def get_user_cover_letter(
    db: AsyncSession,
    cover_letter_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GeneratedCoverLetter:
    """Fetch a single generated cover letter owned by the user."""
    return await get_owned_document(
        db,
        GeneratedCoverLetter,
        cover_letter_id,
        user_id,
        not_found_detail="Cover letter not found",
    )


async def get_cover_letter_download_info(
    db: AsyncSession,
    cover_letter_id: uuid.UUID,
    user: User,
) -> tuple[str, str]:
    """Validate ownership and return (pdf_path, clean_download_filename) for a cover letter."""
    return await get_download_file_info(
        db,
        GeneratedCoverLetter,
        cover_letter_id,
        user,
        filename_prefix="cover-letter",
        not_found_detail="Cover letter not found",
    )


async def delete_user_cover_letter(
    db: AsyncSession,
    cover_letter_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete an owned cover letter record and its generated PDF file."""
    await delete_owned_document(
        db,
        GeneratedCoverLetter,
        cover_letter_id,
        user_id,
        not_found_detail="Cover letter not found",
    )
