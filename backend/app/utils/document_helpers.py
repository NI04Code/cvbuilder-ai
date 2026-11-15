"""Shared database, ownership, and file download/delete helpers for generated job documents."""

import asyncio
import logging
import os
import uuid
from typing import TypeVar

from fastapi import HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import PersonalInfo, ProfileResponse
from app.utils.file_handler import (
    build_document_filename,
    delete_generated_document_file,
)

logger = logging.getLogger(__name__)
DocModelT = TypeVar("DocModelT")


async def get_user_profile_or_400(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> tuple[Profile, ProfileResponse]:
    """Fetch the user's base profile or raise 400 if none has been created yet."""
    db_result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = db_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume profile found. Please upload or save a profile first.",
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


async def get_owned_document_or_404(
    db: AsyncSession,
    model_cls: type[DocModelT],
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
    not_found_detail: str = "Document not found",
) -> DocModelT:
    """Load a generated document row scoped strictly to the authenticated owner."""
    result = await db.execute(
        select(model_cls).where(model_cls.id == doc_id, model_cls.user_id == user_id)  # type: ignore[attr-defined]
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)
    return record


async def resolve_download_display_name(db: AsyncSession, user: User) -> str:
    """Resolve candidate name from profile personal_info (or fallback to account name)."""
    profile_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()
    profile_name = (
        profile.personal_info.get("name")
        if profile and isinstance(profile.personal_info, dict)
        else None
    )
    return profile_name or user.name or "Candidate"


async def build_pdf_download_response(
    db: AsyncSession,
    model_cls: type[DocModelT],
    doc_id: uuid.UUID,
    user: User,
    filename_prefix: str,
    not_found_detail: str = "Document not found",
) -> FileResponse:
    """Validate ownership and file existence, then return the PDF FileResponse with a clean filename."""
    doc = await get_owned_document_or_404(
        db, model_cls, doc_id, user.id, not_found_detail=not_found_detail
    )
    file_path = getattr(doc, "pdf_file_path", None)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on server",
        )

    user_name = await resolve_download_display_name(db, user)
    company_name = getattr(doc, "company_name", None)
    download_filename = build_document_filename(filename_prefix, company_name, user_name)

    return FileResponse(
        path=file_path,
        filename=download_filename,
        media_type="application/pdf",
    )


async def delete_owned_document(
    db: AsyncSession,
    model_cls: type[DocModelT],
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
    not_found_detail: str = "Document not found",
) -> None:
    """Delete an owned generated document record from DB and remove its PDF file from disk."""
    doc = await get_owned_document_or_404(
        db, model_cls, doc_id, user_id, not_found_detail=not_found_detail
    )
    pdf_file_path = getattr(doc, "pdf_file_path", None)
    await db.delete(doc)
    await db.commit()

    try:
        await asyncio.to_thread(delete_generated_document_file, pdf_file_path, user_id)
    except Exception as exc:
        logger.error("Failed to remove PDF file for deleted document %s: %s", doc_id, exc)

