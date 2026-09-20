"""Profile API endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest
from app.security.jwt import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get(
    "/",
    response_model=ProfileResponse,
    summary="Get current user's profile",
)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Fetch the parsed resume profile for the currently authenticated user."""
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please upload a resume first.",
        )

    return ProfileResponse.model_validate(profile)


@router.put(
    "/",
    response_model=ProfileResponse,
    summary="Create or update user profile manually",
)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """
    Create or update the user's profile with manually provided data.
    Merges with existing profile data if the profile already exists.
    """
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()

    if profile:
        # Update existing profile — only overwrite fields that are provided
        if data.personal_info is not None:
            profile.personal_info = data.personal_info.model_dump()
        if data.summary is not None:
            profile.summary = data.summary
        if data.work_experiences is not None:
            profile.work_experiences = [w.model_dump() for w in data.work_experiences]
        if data.education is not None:
            profile.education = [e.model_dump() for e in data.education]
        if data.skills is not None:
            profile.skills = data.skills.model_dump()
        if data.certifications is not None:
            profile.certifications = [c.model_dump() for c in data.certifications]
        if data.projects is not None:
            profile.projects = [p.model_dump() for p in data.projects]
        profile.updated_at = datetime.now(timezone.utc)
    else:
        # Create new profile
        profile = Profile(
            id=uuid.uuid4(),
            user_id=current_user.id,
            personal_info=data.personal_info.model_dump() if data.personal_info else None,
            summary=data.summary,
            work_experiences=[w.model_dump() for w in data.work_experiences] if data.work_experiences else [],
            education=[e.model_dump() for e in data.education] if data.education else [],
            skills=data.skills.model_dump() if data.skills else None,
            certifications=[c.model_dump() for c in data.certifications] if data.certifications else [],
            projects=[p.model_dump() for p in data.projects] if data.projects else [],
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)

    return ProfileResponse.model_validate(profile)

