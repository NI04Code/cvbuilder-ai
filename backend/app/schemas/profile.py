"""Pydantic schemas for profile (parsed resume) data."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Nested profile components ─────────────────────────────────────────────


class PersonalInfo(BaseModel):
    name: str = Field(..., description="Full name")
    email: str | None = Field(None, description="Contact email")
    phone: str | None = Field(None, description="Phone number")
    location: str | None = Field(None, description="City, State/Country")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL")
    portfolio_url: str | None = Field(None, description="Portfolio or personal website")


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
    institution: str = Field(..., description="School or university name")
    degree: str | None = Field(None, description="Degree type (e.g., Bachelor of Science)")
    field: str | None = Field(None, description="Field of study")
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    relevant_coursework: list[str] = Field(default_factory=list, description="Relevant coursework")


class Certification(BaseModel):
    name: str = Field(..., description="Certification name")
    issuer: str | None = Field(None, description="Issuing organization")
    date: str | None = Field(None, description="Date obtained")
    credential_id: str | None = None


class Project(BaseModel):
    name: str = Field(..., description="Project name")
    description: str | None = Field(None, description="Brief project description")
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None


class SkillSet(BaseModel):
    technical: list[str] = Field(default_factory=list, description="Technical skills")
    soft: list[str] = Field(default_factory=list, description="Soft skills")
    languages: list[str] = Field(default_factory=list, description="Spoken languages")
    tools: list[str] = Field(default_factory=list, description="Tools and platforms")


# ── Resume Profile (used for LLM structured output) ──────────────────────


class ResumeProfile(BaseModel):
    """Full structured resume profile — used as the LLM extraction target."""

    personal_info: PersonalInfo
    summary: str = Field(..., description="Professional summary or objective")
    work_experiences: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
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
    skills: SkillSet | None = None
    certifications: list[Certification] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    parsed_at: datetime | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    """Manual profile update request from the user."""

    personal_info: PersonalInfo | None = None
    summary: str | None = None
    work_experiences: list[WorkExperience] | None = None
    education: list[Education] | None = None
    skills: SkillSet | None = None
    certifications: list[Certification] | None = None
    projects: list[Project] | None = None
