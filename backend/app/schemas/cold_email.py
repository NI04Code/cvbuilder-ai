"""Pydantic schemas for cold email generation request/response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.document import JobTargetedRequest
from app.security.sanitizer import sanitize_text


class ColdEmailGenerateRequest(JobTargetedRequest):
    """Request payload for generating a concise recruiter cold email."""

    recruiter_name: str | None = Field(
        None,
        max_length=255,
        description="Optional recruiter or hiring manager name to personalize the greeting",
    )

    @field_validator("recruiter_name", mode="before")
    @classmethod
    def sanitize_recruiter_name(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = sanitize_text(value)
            return cleaned or None
        return value


class ColdEmailContent(BaseModel):
    """Concise recruiter cold email with a compelling subject and opening hook."""

    subject: str = Field(
        ...,
        min_length=5,
        max_length=150,
        description="Short, value-first email subject line referencing the role or key impact",
    )
    email_body: str = Field(
        ...,
        min_length=50,
        description="Concise plain-text cold email (90-150 words) with personalized hook, proof, and low-friction CTA",
    )


class ColdEmailResponse(BaseModel):
    """Generated cold email returned to the frontend."""

    id: uuid.UUID
    job_title: str | None = None
    company_name: str | None = None
    recruiter_name: str | None = None
    job_description: str
    subject: str
    email_body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ColdEmailListItem(BaseModel):
    """Abbreviated cold email metadata for list views."""

    id: uuid.UUID
    job_title: str | None = None
    company_name: str | None = None
    recruiter_name: str | None = None
    subject: str
    created_at: datetime

    model_config = {"from_attributes": True}
