"""Pydantic schemas for user-related request/response models."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.security.sanitizer import sanitize_text

# ── Request Schemas ───────────────────────────────────────────────────────


class OAuthVerifyRequest(BaseModel):
    """Payload sent from NextAuth.js after a successful OAuth sign-in."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., pattern=r"^(google|github)$")
    provider_account_id: str = Field(..., min_length=1, max_length=255)
    avatar_url: str | None = Field(None, max_length=2048)
    access_token: str | None = None  # Provider access token (optional)


class RegisterRequest(BaseModel):
    """Payload for creating a manual email/password user account."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, value: object) -> object:
        if isinstance(value, str):
            return sanitize_text(value)
        return value

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password", mode="after")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


class LoginRequest(BaseModel):
    """Payload for manual email/password sign-in."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class TokenRefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


# ── Response Schemas ──────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    """JWT token pair returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class UserResponse(BaseModel):
    """Public user data returned to the frontend."""

    id: uuid.UUID
    email: str
    name: str
    avatar_url: str | None = None
    is_active: bool
    has_profile: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Combined auth response: user data + tokens."""

    user: UserResponse
    tokens: TokenResponse
