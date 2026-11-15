"""Pydantic schemas for CV generation request/response models."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.document import (
    JOB_DESCRIPTION_MAX_LENGTH,
    JOB_DESCRIPTION_MIN_LENGTH,
    JobTargetedRequest,
)
from app.schemas.profile import Certification, Education, LeadershipActivity, Project

SectionKey = Literal[
    "summary",
    "experience",
    "education",
    "leadership",
    "certifications",
    "projects",
    "skills",
]

DEFAULT_SECTION_ORDER: list[SectionKey] = [
    "summary",
    "experience",
    "education",
    "leadership",
    "certifications",
    "projects",
    "skills",
]


# ── Request Schemas ───────────────────────────────────────────────────────


CVGenerateRequest = JobTargetedRequest


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


class SkillCategory(BaseModel):
    """A single categorized row of skills in the tailored CV."""

    category: str = Field(
        ...,
        description="Concise category label (e.g., 'Languages & Frameworks', 'Cloud & DevOps', 'Databases & Tools')",
    )
    items: list[str] = Field(
        default_factory=list,
        description=(
            "Skills in this category ranked from most relevant to least relevant for the target role, "
            "concise enough to fit on a single row"
        ),
    )


class TailoredCV(BaseModel):
    """Complete tailored CV content — output from the CV generation agent."""

    professional_summary: str | None = Field(
        None,
        description="Optional tailored professional summary for this specific job; null or empty string if omitted",
    )
    work_experiences: list[TailoredExperience] = Field(
        default_factory=list,
        description="Required work experiences section from the candidate's profile with bullets tailored to the target job",
    )
    education: list[Education] = Field(
        default_factory=list,
        description="Required education section from the candidate's profile",
    )
    leadership_activities: list[LeadershipActivity] = Field(
        default_factory=list,
        description="Optional leadership and organizational activities from the candidate's profile",
    )
    certifications: list[Certification] = Field(
        default_factory=list,
        description="Optional certifications from the candidate's profile",
    )
    projects: list[Project] = Field(
        default_factory=list,
        description="Optional projects from the candidate's profile",
    )
    skills: list[SkillCategory] = Field(
        default_factory=list,
        description=(
            "Optional categorized skills list (maximum 3 categories). Each category must span only 1 row "
            "and rank skills from most relevant to least relevant."
        ),
    )

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, value: object) -> list[dict | SkillCategory]:
        """Support legacy flat list[str] from older stored CVs and enforce max 3 categories."""
        if not value or not isinstance(value, list):
            return []
        if all(isinstance(item, str) for item in value):
            cleaned = [s.strip() for s in value if s and s.strip()]
            return [{"category": "Technical Skills", "items": cleaned}] if cleaned else []
        normalized: list[dict | SkillCategory] = []
        for entry in value:
            if isinstance(entry, SkillCategory):
                if entry.items:
                    normalized.append(entry)
            elif isinstance(entry, dict):
                items = [str(s).strip() for s in (entry.get("items") or []) if str(s).strip()]
                cat = str(entry.get("category") or "Skills").strip()
                if items:
                    normalized.append({"category": cat, "items": items})
        return normalized[:3]
    keywords_matched: list[str] = Field(
        default_factory=list,
        description="Job description keywords found in the tailored CV",
    )
    section_order: list[SectionKey] = Field(
        default_factory=lambda: list(DEFAULT_SECTION_ORDER),
        description=(
            "Ordered list of sections. Must follow: 'summary', then 'experience' and 'education' "
            "(only these two may be swapped with each other), then 'leadership', 'certifications', "
            "'projects', 'skills'."
        ),
    )
    ats_score: float = Field(
        ..., ge=0, le=100, description="Estimated ATS match percentage"
    )

    @field_validator("section_order", mode="after")
    @classmethod
    def enforce_section_order(cls, value: list[SectionKey]) -> list[SectionKey]:
        """Enforce fixed section progression while allowing experience/education swap."""
        exp_edu = [s for s in value if s in ("experience", "education")]
        # Preserve unique relative order of experience and education; fill any missing one
        normalized_core: list[SectionKey] = []
        for s in exp_edu:
            if s not in normalized_core:
                normalized_core.append(s)
        for core in ("experience", "education"):
            if core not in normalized_core:
                normalized_core.append(core)

        return [
            "summary",
            *normalized_core,
            "leadership",
            "certifications",
            "projects",
            "skills",
        ]


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
