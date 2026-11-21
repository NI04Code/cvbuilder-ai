"""Database queries for the Profile model."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile


async def has_profile(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Return True if the user already has a stored Profile row."""
    result = await db.execute(
        select(Profile.id).where(Profile.user_id == user_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Profile | None:
    """Fetch a user's Profile row by user_id."""
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()


async def save_profile(db: AsyncSession, profile: Profile, *, is_new: bool = False) -> Profile:
    """Persist a new or updated Profile row and return the refreshed instance."""
    if is_new:
        db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
