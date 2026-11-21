"""Shared pytest fixtures and mock factories for backend unit tests."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cover_letter import GeneratedCoverLetter
from app.models.generated_cv import GeneratedCV
from app.models.profile import Profile
from app.models.user import OAuthAccount, User
from app.schemas.ats_checker import (
    ATSCheckResult,
    ATSKeywordAnalysis,
    ATSSectionScore,
    ParsedCVDocument,
)
from app.schemas.cv import JobRequirements, SkillCategory, TailoredCV, TailoredExperience
from app.schemas.profile import Education, PersonalInfo, ProfileResponse


def make_scalar_result(value: object) -> MagicMock:
    """Create a mock SQLAlchemy Result whose scalar_one_or_none() returns `value`."""
    res = MagicMock()
    res.scalar_one_or_none.return_value = value
    return res


def make_scalars_result(items: list[object]) -> MagicMock:
    """Create a mock SQLAlchemy Result whose scalars().all() returns `items`."""
    scalars = MagicMock()
    scalars.all.return_value = items
    res = MagicMock()
    res.scalars.return_value = scalars
    return res


def make_user(**overrides: object) -> User:
    now = datetime.now(timezone.utc)
    defaults = {
        "id": uuid.uuid4(),
        "email": "candidate@example.com",
        "name": "Alex Candidate",
        "avatar_url": "https://example.com/avatar.png",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return User(**defaults)


def make_oauth_account(user_id: uuid.UUID, **overrides: object) -> OAuthAccount:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "provider": "google",
        "provider_account_id": "acct-123",
        "access_token": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return OAuthAccount(**defaults)


def make_personal_info(**overrides: object) -> PersonalInfo:
    defaults = {
        "name": "Alex Candidate",
        "email": "candidate@example.com",
        "phone": "+1 555-010-9999",
        "location": "Jakarta, Indonesia",
        "linkedin_url": "https://linkedin.com/in/alex",
        "portfolio_url": "https://alex.dev",
        "other_url": "https://github.com/alex",
    }
    defaults.update(overrides)
    return PersonalInfo(**defaults)


def make_profile(user_id: uuid.UUID | None = None, **overrides: object) -> Profile:
    now = datetime.now(timezone.utc)
    defaults = {
        "id": uuid.uuid4(),
        "user_id": user_id or uuid.uuid4(),
        "personal_info": make_personal_info().model_dump(),
        "summary": "Backend engineer experienced in Python and FastAPI.",
        "work_experiences": [
            {
                "company": "Acme Corp",
                "title": "Software Engineer",
                "start_date": "2022-01",
                "end_date": "Present",
                "location": "Remote",
                "bullets": ["Reduced API latency by 35% across 10 microservices."],
            }
        ],
        "education": [
            {
                "institution": "State University",
                "degree": "Bachelor of Science",
                "field": "Computer Science",
                "start_date": "2018-08",
                "end_date": "2022-05",
                "gpa": "3.8",
                "relevant_coursework": ["Algorithms"],
            }
        ],
        "leadership_activities": [],
        "skills": {
            "technical": ["Python", "FastAPI", "PostgreSQL"],
            "soft": ["Communication"],
            "languages": ["English"],
            "tools": ["Docker"],
        },
        "certifications": [],
        "projects": [],
        "raw_resume_text": "Alex Candidate\nSoftware Engineer",
        "source_file_path": "/tmp/resume.pdf",
        "parsed_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Profile(**defaults)


def make_profile_response(user_id: uuid.UUID | None = None) -> ProfileResponse:
    return ProfileResponse.model_validate(make_profile(user_id=user_id))


def make_tailored_cv(**overrides: object) -> TailoredCV:
    defaults = {
        "professional_summary": "Backend engineer with 3+ years building Python APIs.",
        "work_experiences": [
            TailoredExperience(
                company="Acme Corp",
                title="Software Engineer",
                start_date="2022-01",
                end_date="Present",
                location="Remote",
                bullets=["Reduced API latency by 35% across 10 microservices."],
            )
        ],
        "education": [
            Education(
                institution="State University",
                degree="B.S.",
                field="Computer Science",
                start_date="2018-08",
                end_date="2022-05",
                gpa="3.8",
                relevant_coursework=["Distributed Systems"],
            )
        ],
        "leadership_activities": [],
        "certifications": [],
        "projects": [],
        "skills": [
            SkillCategory(category="Languages", items=["Python", "SQL"]),
            SkillCategory(category="Frameworks", items=["FastAPI", "Docker"]),
        ],
        "keywords_matched": ["Python", "FastAPI"],
        "ats_score": 88.0,
    }
    defaults.update(overrides)
    return TailoredCV(**defaults)


def make_generated_cv(user_id: uuid.UUID | None = None, **overrides: object) -> GeneratedCV:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": user_id or uuid.uuid4(),
        "profile_id": uuid.uuid4(),
        "job_title": "Backend Engineer",
        "company_name": "Acme Corp",
        "job_description": "Looking for a Backend Engineer skilled in Python and FastAPI." * 2,
        "tailored_content": make_tailored_cv().model_dump(),
        "pdf_file_path": "/tmp/cv.pdf",
        "ats_score": 88.0,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return GeneratedCV(**defaults)


def make_generated_cover_letter(
    user_id: uuid.UUID | None = None, **overrides: object
) -> GeneratedCoverLetter:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": user_id or uuid.uuid4(),
        "profile_id": uuid.uuid4(),
        "job_title": "Backend Engineer",
        "company_name": "Acme Corp",
        "job_description": "Looking for a Backend Engineer skilled in Python and FastAPI." * 2,
        "cover_letter_text": "Dear Hiring Manager,\n\nI am excited to apply.\n\nSincerely,\nAlex",
        "pdf_file_path": "/tmp/cl.pdf",
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return GeneratedCoverLetter(**defaults)


def make_job_requirements(**overrides: object) -> JobRequirements:
    defaults = {
        "job_title": "Backend Engineer",
        "company": "Acme Corp",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["PostgreSQL"],
        "required_experience_years": 3,
        "key_responsibilities": ["Build scalable APIs"],
        "education_requirements": ["BS CS"],
        "keywords": ["Python", "FastAPI", "PostgreSQL"],
    }
    defaults.update(overrides)
    return JobRequirements(**defaults)


def make_parsed_cv_doc(**overrides: object) -> ParsedCVDocument:
    cv = make_tailored_cv()
    doc = ParsedCVDocument.from_tailored_cv(cv, make_personal_info())
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


def make_ats_check_result(**overrides: object) -> ATSCheckResult:
    defaults = {
        "overall_score": 85,
        "candidate_level": "Mid-Level",
        "target_role": "Backend Engineer",
        "sections": [
            ATSSectionScore(
                section_name="Contact Information",
                score=100,
                present=True,
                weight=0.05,
                feedback="Complete contact details.",
                suggestions=[],
            ),
            ATSSectionScore(
                section_name="Work Experience",
                score=85,
                present=True,
                weight=0.40,
                feedback="Good metrics.",
                suggestions=["Add latency numbers to older role."],
            ),
            ATSSectionScore(
                section_name="Skills",
                score=90,
                present=True,
                weight=0.20,
                feedback="Well-categorized skills.",
                suggestions=["Include Kubernetes if used."],
            ),
            ATSSectionScore(
                section_name="Education",
                score=90,
                present=True,
                weight=0.10,
                feedback="Relevant CS degree.",
                suggestions=["Highlight relevant coursework."],
            ),
            ATSSectionScore(
                section_name="Formatting",
                score=100,
                present=True,
                weight=0.10,
                feedback="Clean formatting.",
                suggestions=[],
            ),
        ],
        "keyword_analysis": ATSKeywordAnalysis(
            detected_keywords=["Python", "FastAPI"],
            missing_common_keywords=["Kubernetes"],
            keyword_density_rating="Adequate",
        ),
        "formatting_issues": [],
        "strengths": ["Clear quantified impact."],
        "improvements": ["Highlight cloud orchestration tools."],
        "summary": "Strong backend resume with clean ATS structure. Adding cloud orchestration terms will further boost alignment.",
    }
    defaults.update(overrides)
    return ATSCheckResult(**defaults)


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)
