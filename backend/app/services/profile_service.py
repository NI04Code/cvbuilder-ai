"""Profile business logic — fetching and updating structured user profiles."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database import profile_repo
from app.models.profile import Profile
from app.schemas.profile import ProfileUpdateRequest


async def get_profile_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Profile:
    """Return the user's parsed resume profile or raise NotFoundError."""
    profile = await profile_repo.get_by_user_id(db, user_id)
    if not profile:
        raise NotFoundError("Profile not found. Please upload a resume first.")
    return profile


async def upsert_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: ProfileUpdateRequest,
) -> Profile:
    """Create or partially update the user's profile with manually supplied fields."""
    profile = await profile_repo.get_by_user_id(db, user_id)
    is_new = profile is None

    if profile:
        if data.personal_info is not None:
            profile.personal_info = data.personal_info.model_dump()
        if data.summary is not None:
            profile.summary = data.summary
        if data.work_experiences is not None:
            profile.work_experiences = [w.model_dump() for w in data.work_experiences]
        if data.education is not None:
            profile.education = [e.model_dump() for e in data.education]
        if data.leadership_activities is not None:
            profile.leadership_activities = [
                l.model_dump() for l in data.leadership_activities
            ]
        if data.skills is not None:
            profile.skills = data.skills.model_dump()
        if data.certifications is not None:
            profile.certifications = [c.model_dump() for c in data.certifications]
        if data.projects is not None:
            profile.projects = [p.model_dump() for p in data.projects]
        profile.updated_at = datetime.now(timezone.utc)
    else:
        profile = Profile(
            id=uuid.uuid4(),
            user_id=user_id,
            personal_info=data.personal_info.model_dump() if data.personal_info else None,
            summary=data.summary,
            work_experiences=(
                [w.model_dump() for w in data.work_experiences]
                if data.work_experiences
                else []
            ),
            education=(
                [e.model_dump() for e in data.education] if data.education else []
            ),
            leadership_activities=(
                [l.model_dump() for l in data.leadership_activities]
                if data.leadership_activities
                else []
            ),
            skills=data.skills.model_dump() if data.skills else None,
            certifications=(
                [c.model_dump() for c in data.certifications]
                if data.certifications
                else []
            ),
            projects=[p.model_dump() for p in data.projects] if data.projects else [],
        )

    return await profile_repo.save_profile(db, profile, is_new=is_new)
