"""Resume upload and parsing business logic."""

import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.resume_agent import process_resume
from app.core.exceptions import BadRequestError, GenerationError
from app.database import profile_repo
from app.models.profile import Profile
from app.schemas.profile import Certification, WorkExperience
from app.utils.file_handler import save_upload_file

logger = logging.getLogger(__name__)

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


async def upload_and_parse_resume(
    db: AsyncSession,
    user_id: uuid.UUID,
    file: UploadFile,
) -> Profile:
    """Save an uploaded PDF resume, parse it via LangGraph, and upsert the user's Profile."""
    try:
        file_path = await save_upload_file(file, user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise BadRequestError(f"Error saving file: {exc}") from exc

    try:
        result = await process_resume(str(file_path))

        if result.get("error"):
            raise GenerationError(result["error"])

        parsed_profile = result.get("profile")
        if not parsed_profile:
            raise GenerationError("Failed to extract profile data from the resume.")

        profile = await profile_repo.get_by_user_id(db, user_id)
        is_new = profile is None

        sorted_work = _sort_work_experiences_desc(parsed_profile.work_experiences or [])
        sorted_certs = _sort_certifications_desc(parsed_profile.certifications or [])

        if profile:
            profile.personal_info = (
                parsed_profile.personal_info.model_dump()
                if parsed_profile.personal_info
                else None
            )
            profile.summary = parsed_profile.summary
            profile.work_experiences = [w.model_dump() for w in sorted_work]
            profile.education = [e.model_dump() for e in (parsed_profile.education or [])]
            profile.leadership_activities = [
                l.model_dump() for l in (parsed_profile.leadership_activities or [])
            ]
            profile.skills = (
                parsed_profile.skills.model_dump() if parsed_profile.skills else None
            )
            profile.certifications = [c.model_dump() for c in sorted_certs]
            profile.projects = [p.model_dump() for p in (parsed_profile.projects or [])]
            profile.raw_resume_text = result["raw_text"]
            profile.source_file_path = str(file_path)
            profile.parsed_at = datetime.now(timezone.utc)
        else:
            profile = Profile(
                user_id=user_id,
                personal_info=(
                    parsed_profile.personal_info.model_dump()
                    if parsed_profile.personal_info
                    else None
                ),
                summary=parsed_profile.summary,
                work_experiences=[w.model_dump() for w in sorted_work],
                education=[e.model_dump() for e in (parsed_profile.education or [])],
                leadership_activities=[
                    l.model_dump() for l in (parsed_profile.leadership_activities or [])
                ],
                skills=(
                    parsed_profile.skills.model_dump() if parsed_profile.skills else None
                ),
                certifications=[c.model_dump() for c in sorted_certs],
                projects=[p.model_dump() for p in (parsed_profile.projects or [])],
                raw_resume_text=result["raw_text"],
                source_file_path=str(file_path),
                parsed_at=datetime.now(timezone.utc),
            )

        return await profile_repo.save_profile(db, profile, is_new=is_new)
    except Exception:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception as cleanup_exc:
            logger.warning("Failed to clean up orphaned upload %s: %s", file_path, cleanup_exc)
        raise
