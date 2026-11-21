"""Resume upload and parsing API endpoints — HTTP layer delegating to resume_service."""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.profile import ProfileResponse
from app.security.jwt import get_current_user
from app.security.rate_limiter import limiter
from app.services.resume_service import upload_and_parse_resume

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
    """Uploads a resume PDF, parses it via resume_service, and returns the structured profile."""
    profile = await upload_and_parse_resume(db, current_user.id, file)
    return ProfileResponse.model_validate(profile)
