"""Pydantic schemas for CV generation request/response models."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.profile import Certification, Education, Project

SectionKey = Literal[
    "summary",
    "skills",
    "experience",
    "education",
    "certifications",
    "projects",
]


# ── Request Schemas ───────────────────────────────────────────────────────


class CVGenerateRequest(BaseModel):
    """Request to generate a tailored ATS CV."""

    job_description: str = Field(
        ..., min_length=50, max_length=10000, description="Full job description text"
    )
    job_title: str | None = Field(None, max_length=255, description="Target job title")
    company_name: str | None = Field(None, max_length=255, description="Target company")


# ── Tailored CV content (LLM output) ─────────────────────────────────────


class TailoredBullet(BaseModel):
    original: str = Field(..., description="Original bullet point from resume")
    tailored: str = Field(..., description="Rewritten bullet point optimized for the job")


class TailoredExperience(BaseModel):
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    bullets: list[str] = Field(
        default_factory=list, description="Tailored bullet points"
    )


class TailoredCV(BaseModel):
    """Complete tailored CV content — output from the CV generation agent."""

    professional_summary: str = Field(
        ..., description="Tailored professional summary for this specific job"
    )
    work_experiences: list[TailoredExperience] = Field(
        default_factory=list,
        description="All work experiences from the candidate's profile with bullets tailored to the target job",
    )
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(
        default_factory=list,
        description="Curated skills list prioritized for the job",
    )
    certifications: list[Certification] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    keywords_matched: list[str] = Field(
        default_factory=list,
        description="Job description keywords found in the tailored CV",
    )
    section_order: list[SectionKey] = Field(
        default_factory=lambda: [
            "summary",
            "skills",
            "experience",
            "education",
            "certifications",
            "projects",
        ],
        description="Complete order of all 6 sections to display. Must include 'summary', 'skills', 'experience', 'education', 'certifications', 'projects'.",
    )
    ats_score: float = Field(
        ..., ge=0, le=100, description="Estimated ATS match percentage"
    )


# ── Job Description Analysis (intermediate LLM output) ───────────────────


class JobRequirements(BaseModel):
    """Structured extraction of key requirements from a job description."""

    job_title: str = Field(..., description="Extracted or provided job title")
    company: str | None = Field(None, description="Company name if mentioned")
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_experience_years: int | None = Field(
        None, description="Minimum years of experience required"
    )
    key_responsibilities: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(
        default_factory=list,
        description="Important ATS keywords to include in the CV",
    )


# ── API Response Schemas ──────────────────────────────────────────────────


class CVResponse(BaseModel):
    """Generated CV metadata returned to the frontend."""

    id: uuid.UUID
    job_title: str | None = None
    company_name: str | None = None
    job_description: str
    ats_score: float | None = None
    tailored_content: TailoredCV | None = None
    pdf_file_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CVListItem(BaseModel):
    """Abbreviated CV data for list views."""

    id: uuid.UUID
    job_title: str | None = None
    company_name: str | None = None
    ats_score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
