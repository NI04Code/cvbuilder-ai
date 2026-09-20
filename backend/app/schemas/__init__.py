"""Pydantic schema exports."""

from app.schemas.cv import (
    CVGenerateRequest,
    CVListItem,
    CVResponse,
    JobRequirements,
    TailoredCV,
)
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    ResumeProfile,
)
from app.schemas.user import (
    AuthResponse,
    OAuthVerifyRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)

__all__ = [
    "OAuthVerifyRequest",
    "TokenRefreshRequest",
    "TokenResponse",
    "UserResponse",
    "AuthResponse",
    "ResumeProfile",
    "ProfileResponse",
    "ProfileUpdateRequest",
    "CVGenerateRequest",
    "CVResponse",
    "CVListItem",
    "TailoredCV",
    "JobRequirements",
]
