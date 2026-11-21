"""Profile API endpoints — HTTP layer delegating to profile_service."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest
from app.security.jwt import get_current_user
from app.services.profile_service import get_profile_by_user_id, upsert_profile

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
    profile = await get_profile_by_user_id(db, current_user.id)
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
    """Create or update the user's profile with manually provided data."""
    profile = await upsert_profile(db, current_user.id, data)
    return ProfileResponse.model_validate(profile)
