"""Pydantic schemas for cover letter generation request/response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.document import JobTargetedRequest

CoverLetterGenerateRequest = JobTargetedRequest


class CoverLetterContent(BaseModel):
    """Concise plain-text cover letter tailored to a job description (fits max 1 A4 page)."""

    cover_letter_text: str = Field(
        ...,
        min_length=50,
        description="Complete plain-text cover letter (greeting, 3-4 concise body paragraphs, sign-off)",
    )


class CoverLetterResponse(BaseModel):
    """Generated cover letter returned to the frontend."""

    id: uuid.UUID
    job_title: str | None = None
    company_name: str | None = None
    job_description: str
    cover_letter_text: str
    pdf_file_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CoverLetterListItem(BaseModel):
    """Abbreviated cover letter metadata for list views."""

    id: uuid.UUID
    job_title: str | None = None
    company_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

