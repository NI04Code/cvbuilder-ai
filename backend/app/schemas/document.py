"""Shared request and metadata-tagged history schemas for generated job documents."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.security.sanitizer import sanitize_text

DocumentType = Literal["cv", "cover_letter"]

JOB_DESCRIPTION_MIN_LENGTH = 50
JOB_DESCRIPTION_MAX_LENGTH = 2500


class JobTargetedRequest(BaseModel):
    """Shared request payload for generating a job-targeted document from a base profile."""

    job_description: str = Field(
        ...,
        min_length=JOB_DESCRIPTION_MIN_LENGTH,
        max_length=JOB_DESCRIPTION_MAX_LENGTH,
        description="Full job description text (50–2500 characters)",
    )
    job_title: str | None = Field(None, max_length=255, description="Target job title")
    company_name: str | None = Field(None, max_length=255, description="Target company")

    @field_validator("job_description", "job_title", "company_name", mode="before")
    @classmethod
    def sanitize_inputs(cls, value: object) -> object:
        if isinstance(value, str):
            return sanitize_text(value)
        return value


class DocumentHistoryItem(BaseModel):
    """Unified, metadata-tagged generated document summary returned for dashboard listing & filtering."""

    id: uuid.UUID
    document_type: DocumentType
    job_title: str | None = None
    company_name: str | None = None
    ats_score: float | None = None
    created_at: datetime

