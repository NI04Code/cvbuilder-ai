"""Resume upload and parsing API endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.resume_agent import process_resume
from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileResponse
from app.security.jwt import get_current_user
from app.security.rate_limiter import limiter
from app.utils.file_handler import save_upload_file

router = APIRouter(prefix="/resume", tags=["Resume"])


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

    if profile:
        # Update existing
        profile.personal_info = parsed_profile.personal_info.model_dump() if parsed_profile.personal_info else None
        profile.summary = parsed_profile.summary
        profile.work_experiences = [w.model_dump() for w in parsed_profile.work_experiences]
        profile.education = [e.model_dump() for e in parsed_profile.education]
        profile.skills = parsed_profile.skills.model_dump() if parsed_profile.skills else None
        profile.certifications = [c.model_dump() for c in parsed_profile.certifications]
        profile.projects = [p.model_dump() for p in parsed_profile.projects]
        profile.raw_resume_text = result["raw_text"]
        profile.source_file_path = str(file_path)
        profile.parsed_at = datetime.now(timezone.utc)
    else:
        # Create new
        profile = Profile(
            user_id=current_user.id,
            personal_info=parsed_profile.personal_info.model_dump() if parsed_profile.personal_info else None,
            summary=parsed_profile.summary,
            work_experiences=[w.model_dump() for w in parsed_profile.work_experiences],
            education=[e.model_dump() for e in parsed_profile.education],
            skills=parsed_profile.skills.model_dump() if parsed_profile.skills else None,
            certifications=[c.model_dump() for c in parsed_profile.certifications],
            projects=[p.model_dump() for p in parsed_profile.projects],
            raw_resume_text=result["raw_text"],
            source_file_path=str(file_path),
            parsed_at=datetime.now(timezone.utc),
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)

    return ProfileResponse.model_validate(profile)
