"""Shared document business logic — profile validation, ownership enforcement, downloads, deletion, and history."""

import asyncio
import logging
import os
import uuid
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.database import document_repo, profile_repo
from app.models.cold_email import GeneratedColdEmail
from app.models.cover_letter import GeneratedCoverLetter
from app.models.generated_cv import GeneratedCV
from app.models.profile import Profile
from app.models.user import User
from app.schemas.document import DocumentHistoryItem, DocumentType
from app.schemas.profile import PersonalInfo, ProfileResponse
from app.utils.file_handler import (
    build_document_filename,
    delete_generated_document_file,
)

logger = logging.getLogger(__name__)
DocModelT = TypeVar("DocModelT")


async def get_user_profile_for_generation(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> tuple[Profile, ProfileResponse]:
    """Fetch the user's base profile or raise BadRequestError if none exists yet."""
    profile = await profile_repo.get_by_user_id(db, user_id)
    if not profile:
        raise BadRequestError(
            "No resume profile found. Please upload or save a profile first."
        )
    return profile, ProfileResponse.model_validate(profile)


def resolve_candidate_identity(
    profile_response: ProfileResponse,
    user: User,
) -> tuple[PersonalInfo, str]:
    """Ensure a valid PersonalInfo and candidate display name exist for rendering & filenames."""
    personal_info = profile_response.personal_info
    if not personal_info:
        personal_info = PersonalInfo(name=user.name or "Candidate")
    user_name = personal_info.name or user.name or "Candidate"
    return personal_info, user_name


async def get_owned_document(
    db: AsyncSession,
    model_cls: type[DocModelT],
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
    not_found_detail: str = "Document not found",
) -> DocModelT:
    """Load a generated document row scoped strictly to the authenticated owner."""
    record = await document_repo.get_owned_document(db, model_cls, doc_id, user_id)
    if not record:
        raise NotFoundError(not_found_detail)
    return record


async def resolve_download_display_name(db: AsyncSession, user: User) -> str:
    """Resolve candidate name from profile personal_info (or fallback to account name)."""
    profile = await profile_repo.get_by_user_id(db, user.id)
    profile_name = (
        profile.personal_info.get("name")
        if profile and isinstance(profile.personal_info, dict)
        else None
    )
    return profile_name or user.name or "Candidate"


async def get_download_file_info(
    db: AsyncSession,
    model_cls: type[DocModelT],
    doc_id: uuid.UUID,
    user: User,
    filename_prefix: str,
    not_found_detail: str = "Document not found",
) -> tuple[str, str]:
    """Validate ownership and file existence, returning (file_path, clean_download_filename)."""
    doc = await get_owned_document(
        db, model_cls, doc_id, user.id, not_found_detail=not_found_detail
    )
    file_path = getattr(doc, "pdf_file_path", None)
    if not file_path or not os.path.exists(file_path):
        raise NotFoundError("PDF file not found on server")

    user_name = await resolve_download_display_name(db, user)
    company_name = getattr(doc, "company_name", None)
    download_filename = build_document_filename(filename_prefix, company_name, user_name)
    return file_path, download_filename


async def delete_owned_document(
    db: AsyncSession,
    model_cls: type[DocModelT],
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
    not_found_detail: str = "Document not found",
) -> None:
    """Delete an owned generated document record from DB and remove its PDF file from disk."""
    doc = await get_owned_document(
        db, model_cls, doc_id, user_id, not_found_detail=not_found_detail
    )
    pdf_file_path = getattr(doc, "pdf_file_path", None)
    await document_repo.delete_document(db, doc)

    try:
        await asyncio.to_thread(delete_generated_document_file, pdf_file_path, user_id)
    except Exception as exc:
        logger.error("Failed to remove PDF file for deleted document %s: %s", doc_id, exc)


async def list_unified_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_type: DocumentType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[DocumentHistoryItem]:
    """Return user-owned CVs and/or cover letters tagged with `document_type` sorted newest-first."""
    items: list[DocumentHistoryItem] = []
    fetch_cap = limit + offset

    if document_type in (None, "cv"):
        cvs = await document_repo.list_by_user(
            db, GeneratedCV, user_id, limit=fetch_cap, offset=0
        )
        for cv in cvs:
            items.append(
                DocumentHistoryItem(
                    id=cv.id,
                    document_type="cv",
                    job_title=cv.job_title,
                    company_name=cv.company_name,
                    ats_score=cv.ats_score,
                    created_at=cv.created_at,
                )
            )

    if document_type in (None, "cover_letter"):
        cover_letters = await document_repo.list_by_user(
            db, GeneratedCoverLetter, user_id, limit=fetch_cap, offset=0
        )
        for cl in cover_letters:
            items.append(
                DocumentHistoryItem(
                    id=cl.id,
                    document_type="cover_letter",
                    job_title=cl.job_title,
                    company_name=cl.company_name,
                    ats_score=None,
                    created_at=cl.created_at,
                )
            )

    if document_type in (None, "cold_email"):
        cold_emails = await document_repo.list_by_user(
            db, GeneratedColdEmail, user_id, limit=fetch_cap, offset=0
        )
        for ce in cold_emails:
            items.append(
                DocumentHistoryItem(
                    id=ce.id,
                    document_type="cold_email",
                    job_title=ce.job_title,
                    company_name=ce.company_name,
                    recruiter_name=ce.recruiter_name,
                    ats_score=None,
                    created_at=ce.created_at,
                )
            )

    items.sort(key=lambda item: item.created_at, reverse=True)
    return items[offset : offset + limit]
