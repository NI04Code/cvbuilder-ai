"""Pydantic schemas for job applications tracking request and response payloads."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.security.sanitizer import sanitize_text
from app.utils.url import sanitize_external_url

ApplicationStatus = Literal[
    "saved",
    "applied",
    "interviewing",
    "offer",
    "rejected",
    "withdrawn",
]
WorkMode = Literal["remote", "hybrid", "onsite"]


def _clean_optional_text(value: object) -> object:
    if isinstance(value, str):
        cleaned = sanitize_text(value)
        return cleaned or None
    return value


def _clean_job_url(value: object) -> object:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Job URL must be a valid http(s) URL")
    trimmed = value.strip()
    if not trimmed:
        return None
    normalized = sanitize_external_url(trimmed)
    if not normalized:
        raise ValueError("Job URL must be a valid http(s) URL")
    return normalized


class ApplicationCreateRequest(BaseModel):
    """Request payload for creating a tracked job application."""

    company_name: str = Field(..., min_length=1, max_length=255)
    role_title: str = Field(..., min_length=1, max_length=255)
    job_url: str | None = Field(None, max_length=2048)
    status: ApplicationStatus = Field(default="saved")
    applied_date: date | None = None
    work_mode: WorkMode | None = None
    location: str | None = Field(None, max_length=255)
    salary_range: str | None = Field(None, max_length=120)
    recruiter_name: str | None = Field(None, max_length=255)
    recruiter_contact: str | None = Field(None, max_length=320)
    next_follow_up_date: date | None = None
    notes: str | None = Field(None, max_length=4000)

    @field_validator("company_name", "role_title", mode="before")
    @classmethod
    def sanitize_required_text(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Field must be a non-empty string")
        cleaned = sanitize_text(value)
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator(
        "location",
        "salary_range",
        "recruiter_name",
        "recruiter_contact",
        "notes",
        mode="before",
    )
    @classmethod
    def sanitize_optional_fields(cls, value: object) -> object:
        return _clean_optional_text(value)

    @field_validator("job_url", mode="before")
    @classmethod
    def validate_job_url(cls, value: object) -> object:
        return _clean_job_url(value)


class ApplicationUpdateRequest(BaseModel):
    """Partial update payload for a tracked job application."""

    company_name: str | None = Field(None, min_length=1, max_length=255)
    role_title: str | None = Field(None, min_length=1, max_length=255)
    job_url: str | None = Field(None, max_length=2048)
    status: ApplicationStatus | None = None
    applied_date: date | None = None
    work_mode: WorkMode | None = None
    location: str | None = Field(None, max_length=255)
    salary_range: str | None = Field(None, max_length=120)
    recruiter_name: str | None = Field(None, max_length=255)
    recruiter_contact: str | None = Field(None, max_length=320)
    next_follow_up_date: date | None = None
    notes: str | None = Field(None, max_length=4000)

    @field_validator("company_name", "role_title", mode="before")
    @classmethod
    def sanitize_required_if_set(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Field cannot be null")
        cleaned = sanitize_text(value)
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("status", mode="before")
    @classmethod
    def reject_null_status(cls, value: object) -> object:
        if value is None:
            raise ValueError("Status cannot be null")
        return value

    @field_validator(
        "location",
        "salary_range",
        "recruiter_name",
        "recruiter_contact",
        "notes",
        mode="before",
    )
    @classmethod
    def sanitize_optional_fields(cls, value: object) -> object:
        return _clean_optional_text(value)

    @field_validator("job_url", mode="before")
    @classmethod
    def validate_job_url(cls, value: object) -> object:
        return _clean_job_url(value)


class ApplicationResponse(BaseModel):
    """Job application record returned to the client."""

    id: uuid.UUID
    company_name: str
    role_title: str
    job_url: str | None = None
    status: ApplicationStatus
    applied_date: date | None = None
    work_mode: WorkMode | None = None
    location: str | None = None
    salary_range: str | None = None
    recruiter_name: str | None = None
    recruiter_contact: str | None = None
    next_follow_up_date: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationStatsResponse(BaseModel):
    """Summary counts per pipeline status for the authenticated user."""

    total: int = 0
    saved: int = 0
    applied: int = 0
    interviewing: int = 0
    offer: int = 0
    rejected: int = 0
    withdrawn: int = 0
