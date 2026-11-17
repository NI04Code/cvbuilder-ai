"""Resume upload and parsing API endpoints."""

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.resume_agent import process_resume
from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import Certification, ProfileResponse, WorkExperience
from app.security.jwt import get_current_user
from app.security.rate_limiter import limiter
from app.utils.file_handler import save_upload_file

router = APIRouter(prefix="/resume", tags=["Resume"])

_MONTH_NUMBERS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _parse_date_sort_key(raw: str | None) -> tuple[int, int, int, int]:
    """Return a sortable tuple (tier, year, month, day) for resume date strings."""
    cleaned = (raw or "").strip()
    if not cleaned:
        return (0, 0, 0, 0)
    if cleaned.lower() in {"present", "current", "now"}:
        return (2, 9999, 12, 31)

    if match := re.fullmatch(r"(\d{4})-(\d{2})(?:-(\d{2}))?", cleaned):
        return (1, int(match.group(1)), int(match.group(2)), int(match.group(3) or 1))
    if match := re.fullmatch(r"(\d{1,2})/(\d{4})", cleaned):
        return (1, int(match.group(2)), int(match.group(1)), 1)
    if match := re.fullmatch(r"([A-Za-z]+)\.?\s+(\d{4})", cleaned):
        month = _MONTH_NUMBERS.get(match.group(1).lower())
        if month:
            return (1, int(match.group(2)), month, 1)
    if match := re.fullmatch(r"(\d{4})", cleaned):
        return (1, int(match.group(1)), 1, 1)
    return (0, 0, 0, 0)


def _sort_work_experiences_desc(items: list[WorkExperience]) -> list[WorkExperience]:
    """Sort work experiences newest-first using end_date then start_date."""
    return sorted(
        items,
        key=lambda exp: (
            _parse_date_sort_key(exp.end_date)
            if (exp.end_date or "").strip()
            else _parse_date_sort_key(exp.start_date),
            _parse_date_sort_key(exp.start_date),
        ),
        reverse=True,
    )


def _sort_certifications_desc(items: list[Certification]) -> list[Certification]:
    """Sort certifications newest-first by date obtained."""
    return sorted(items, key=lambda cert: _parse_date_sort_key(cert.date), reverse=True)


@router.post(
    "/upload",
    response_model=ProfileResponse,
    summary="Upload and parse a resume PDF",
)
@limiter.limit("5/minute")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """
    Uploads a resume PDF, parses it using LangGraph and Gemini,
    and stores the structured profile in the database.
    """
    # 1. Save the file securely
    try:
        file_path = await save_upload_file(file, current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error saving file: {e}",
        )

    # 2. Parse the resume using LangGraph agent
    result = await process_resume(str(file_path))
    
    if result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"],
        )
        
    parsed_profile = result.get("profile")
    if not parsed_profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract profile data from the resume.",
        )

    # 3. Store or update the profile in the database
    # Check if user already has a profile
    db_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = db_result.scalar_one_or_none()

    sorted_work = _sort_work_experiences_desc(parsed_profile.work_experiences or [])
    sorted_certs = _sort_certifications_desc(parsed_profile.certifications or [])

    if profile:
        # Update existing
        profile.personal_info = parsed_profile.personal_info.model_dump() if parsed_profile.personal_info else None
        profile.summary = parsed_profile.summary
        profile.work_experiences = [w.model_dump() for w in sorted_work]
        profile.education = [e.model_dump() for e in (parsed_profile.education or [])]
        profile.leadership_activities = [l.model_dump() for l in (parsed_profile.leadership_activities or [])]
        profile.skills = parsed_profile.skills.model_dump() if parsed_profile.skills else None
        profile.certifications = [c.model_dump() for c in sorted_certs]
        profile.projects = [p.model_dump() for p in (parsed_profile.projects or [])]
        profile.raw_resume_text = result["raw_text"]
        profile.source_file_path = str(file_path)
        profile.parsed_at = datetime.now(timezone.utc)
    else:
        # Create new
        profile = Profile(
            user_id=current_user.id,
            personal_info=parsed_profile.personal_info.model_dump() if parsed_profile.personal_info else None,
            summary=parsed_profile.summary,
            work_experiences=[w.model_dump() for w in sorted_work],
            education=[e.model_dump() for e in (parsed_profile.education or [])],
            leadership_activities=[l.model_dump() for l in (parsed_profile.leadership_activities or [])],
            skills=parsed_profile.skills.model_dump() if parsed_profile.skills else None,
            certifications=[c.model_dump() for c in sorted_certs],
            projects=[p.model_dump() for p in (parsed_profile.projects or [])],
            raw_resume_text=result["raw_text"],
            source_file_path=str(file_path),
            parsed_at=datetime.now(timezone.utc),
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)

    return ProfileResponse.model_validate(profile)
