"""Pydantic schemas for profile (parsed resume) data."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.utils.url import sanitize_external_url

_CONTROL_AND_BIDI_RE = re.compile(r"[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]")
_MAX_TAG_ITEMS = 50
_MAX_TAG_LENGTH = 100


def _sanitize_tag_list(items: list[str] | None) -> list[str]:
    """Strip control/bidi characters, collapse whitespace, deduplicate, and bound tag lists."""
    if not items:
        return []
    cleaned_items: list[str] = []
    seen: set[str] = set()
    for raw in items:
        if not isinstance(raw, str):
            continue
        cleaned = raw.replace("\r", " ").replace("\n", " ").replace("\t", " ")
        cleaned = _CONTROL_AND_BIDI_RE.sub("", cleaned)
        cleaned = " ".join(cleaned.split())[:_MAX_TAG_LENGTH].strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned_items.append(cleaned)
        if len(cleaned_items) >= _MAX_TAG_ITEMS:
            break
    return cleaned_items


def _clean_optional_url(value: str | None) -> str | None:
    """Normalize valid http(s) URLs while preserving empty input as None."""
    if value is None or not value.strip():
        return None
    safe = sanitize_external_url(value)
    if safe is not None:
        return safe
    # Preserve bare social placeholder tokens like 'LinkedIn' when parsed from linkless text,
    # but reject dangerous URI schemes.
    lower = value.strip().lower()
    if any(lower.startswith(bad) for bad in ("javascript:", "data:", "vbscript:", "file:")):
        return None
    return value.strip()


# ── Nested profile components ─────────────────────────────────────────────


class PersonalInfo(BaseModel):
    name: str = Field(..., description="Full name")
    email: str | None = Field(None, description="Contact email")
    phone: str | None = Field(None, description="Phone number")
    location: str | None = Field(None, description="City, State/Country")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL")
    portfolio_url: str | None = Field(None, description="Portfolio or personal website")
    other_url: str | None = Field(None, description="Other profile or reference link (e.g., GitHub, Kaggle)")

    @field_validator("linkedin_url", "portfolio_url", "other_url", mode="after")
    @classmethod
    def validate_profile_urls(cls, value: str | None) -> str | None:
        return _clean_optional_url(value)


class WorkExperience(BaseModel):
    company: str = Field(..., description="Company name")
    title: str = Field(..., description="Job title")
    start_date: str | None = Field(None, description="Start date (e.g., Jan 2022)")
    end_date: str | None = Field(None, description="End date or 'Present'")
    location: str | None = Field(None, description="Job location")
    bullets: list[str] = Field(
        default_factory=list,
        description="Bullet point achievements / responsibilities",
    )


class Education(BaseModel):
    institution: str = Field("", description="School or university name")
    degree: str | None = Field(None, description="Degree type (e.g., Bachelor of Science)")
    field: str | None = Field(None, description="Field of study")
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    relevant_coursework: list[str] = Field(
        default_factory=list, description="Relevant coursework"
    )

    @field_validator("relevant_coursework", mode="after")
    @classmethod
    def sanitize_coursework(cls, value: list[str]) -> list[str]:
        return _sanitize_tag_list(value)


class Certification(BaseModel):
    name: str = Field("", description="Certification name")
    issuer: str | None = Field(None, description="Issuing organization")
    date: str | None = Field(None, description="Date obtained")
    credential_id: str | None = None
    url: str | None = Field(None, description="Certification credential or verification URL")

    @field_validator("url", mode="after")
    @classmethod
    def validate_cert_url(cls, value: str | None) -> str | None:
        return _clean_optional_url(value)


class LeadershipActivity(BaseModel):
    organization: str = Field("", description="Organization, club, or academic body name")
    title: str = Field(..., description="Leadership role, position, or activity title")
    start_date: str | None = Field(None, description="Start date (e.g., Aug 2023)")
    end_date: str | None = Field(None, description="End date or 'Present'")
    location: str | None = Field(None, description="Location")
    bullets: list[str] = Field(
        default_factory=list,
        description="Bullet point contributions, leadership impact, or activities",
    )


class Project(BaseModel):
    name: str = Field("", description="Project name")
    description: str | None = Field(None, description="Brief project description")
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None

    @field_validator("url", mode="after")
    @classmethod
    def validate_project_url(cls, value: str | None) -> str | None:
        return _clean_optional_url(value)

    @field_validator("technologies", mode="after")
    @classmethod
    def sanitize_technologies(cls, value: list[str]) -> list[str]:
        return _sanitize_tag_list(value)


class SkillSet(BaseModel):
    technical: list[str] = Field(default_factory=list, description="Technical skills")
    soft: list[str] = Field(default_factory=list, description="Soft skills")
    languages: list[str] = Field(default_factory=list, description="Spoken languages")
    tools: list[str] = Field(default_factory=list, description="Tools and platforms")

    @field_validator("technical", "soft", "languages", "tools", mode="after")
    @classmethod
    def sanitize_skill_lists(cls, value: list[str]) -> list[str]:
        return _sanitize_tag_list(value)


# ── Resume Profile (used for LLM structured output) ──────────────────────


class ResumeProfile(BaseModel):
    """Full structured resume profile — used as the LLM extraction target."""

    personal_info: PersonalInfo
    summary: str = Field("", description="Professional summary or objective")
    work_experiences: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    leadership_activities: list[LeadershipActivity] = Field(default_factory=list)
    skills: SkillSet = Field(default_factory=SkillSet)
    certifications: list[Certification] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)


# ── API Response Schemas ──────────────────────────────────────────────────


class ProfileResponse(BaseModel):
    """Profile data returned to the frontend."""

    id: uuid.UUID
    user_id: uuid.UUID
    personal_info: PersonalInfo | None = None
    summary: str | None = None
    work_experiences: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    leadership_activities: list[LeadershipActivity] = Field(default_factory=list)
    skills: SkillSet | None = None
    certifications: list[Certification] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    parsed_at: datetime | None = None
    updated_at: datetime

    @field_validator("*", mode="before")
    @classmethod
    def coerce_null_lists(cls, v: object, info: ValidationInfo) -> object:
        """Automatically convert SQL NULL to [] for any list field with default_factory=list."""
        if v is None and info.field_name in cls.model_fields:
            if cls.model_fields[info.field_name].default_factory is list:
                return []
        return v

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    """Manual profile update request from the user."""

    personal_info: PersonalInfo | None = None
    summary: str | None = None
    work_experiences: list[WorkExperience] | None = None
    education: list[Education] | None = None
    leadership_activities: list[LeadershipActivity] | None = None
    skills: SkillSet | None = None
    certifications: list[Certification] | None = None
    projects: list[Project] | None = None
