"""CV generation, retrieval, download, and deletion business logic."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cv_agent import process_cv_generation
from app.core.exceptions import GenerationError
from app.database import document_repo
from app.models.generated_cv import GeneratedCV
from app.models.user import User
from app.schemas.cv import CVGenerateRequest
from app.services.document_service import (
    delete_owned_document,
    get_download_file_info,
    get_owned_document,
    get_user_profile_for_generation,
    resolve_candidate_identity,
)
from app.utils.file_handler import build_document_filename, get_generated_document_path
from app.utils.pdf_builder import generate_cv_pdf


async def generate_tailored_cv(
    db: AsyncSession,
    user: User,
    data: CVGenerateRequest,
) -> GeneratedCV:
    """Generate a tailored CV via LangGraph, render its PDF, and persist the record."""
    profile, profile_response = await get_user_profile_for_generation(db, user.id)

    result = await process_cv_generation(profile_response, data, user_name=user.name)
    if result.get("error") or not result.get("tailored_cv"):
        raise GenerationError(result.get("error") or "Failed to generate CV content.")

    tailored_cv = result["tailored_cv"]
    resolved_company = data.company_name or result.get("resolved_company")
    personal_info, user_name = resolve_candidate_identity(profile_response, user)

    cv_id = uuid.uuid4()
    pdf_filename = build_document_filename(
        "cv",
        resolved_company,
        user_name,
        unique_code=cv_id.hex[:8],
    )
    pdf_path = get_generated_document_path(user.id, pdf_filename)

    try:
        await asyncio.to_thread(generate_cv_pdf, tailored_cv, personal_info, str(pdf_path))
    except Exception as exc:
        raise GenerationError(f"Failed to generate PDF: {exc}") from exc

    generated_cv = GeneratedCV(
        id=cv_id,
        user_id=user.id,
        profile_id=profile.id,
        job_description=data.job_description,
        job_title=data.job_title,
        company_name=resolved_company,
        tailored_content=tailored_cv.model_dump(),
        pdf_file_path=str(pdf_path),
        ats_score=tailored_cv.ats_score,
        created_at=datetime.now(timezone.utc),
    )
    return await document_repo.save_document(db, generated_cv)


async def list_user_cvs(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[GeneratedCV]:
    """Return a paginated list of generated CVs owned by the user."""
    return await document_repo.list_by_user(
        db, GeneratedCV, user_id, limit=limit, offset=offset
    )


async def get_user_cv(
    db: AsyncSession,
    cv_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GeneratedCV:
    """Fetch a single generated CV owned by the user."""
    return await get_owned_document(
        db, GeneratedCV, cv_id, user_id, not_found_detail="CV not found"
    )


async def get_cv_download_info(
    db: AsyncSession,
    cv_id: uuid.UUID,
    user: User,
) -> tuple[str, str]:
    """Validate ownership and return (pdf_path, clean_download_filename) for a CV."""
    return await get_download_file_info(
        db,
        GeneratedCV,
        cv_id,
        user,
        filename_prefix="cv",
        not_found_detail="CV not found",
    )


async def delete_user_cv(
    db: AsyncSession,
    cv_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete an owned CV record and its generated PDF file."""
    await delete_owned_document(
        db, GeneratedCV, cv_id, user_id, not_found_detail="CV not found"
    )
