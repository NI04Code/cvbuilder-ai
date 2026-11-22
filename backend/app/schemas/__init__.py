"""Pydantic schema exports."""

from app.schemas.job_applications import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationStatsResponse,
    ApplicationUpdateRequest,
)
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
    LoginRequest,
    OAuthVerifyRequest,
    RegisterRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)

__all__ = [
    "OAuthVerifyRequest",
    "RegisterRequest",
    "LoginRequest",
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
    "ApplicationCreateRequest",
    "ApplicationUpdateRequest",
    "ApplicationResponse",
    "ApplicationStatsResponse",
]
