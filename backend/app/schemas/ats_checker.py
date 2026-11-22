"""Pydantic schemas for the public ATS Checker feature."""

from pydantic import BaseModel, Field

from app.schemas.cv import SkillCategory, TailoredCV, TailoredExperience
from app.schemas.profile import (
    Certification,
    Education,
    LeadershipActivity,
    PersonalInfo,
    Project,
)


class ParsedCVDocument(BaseModel):
    """Structured representation of a CV parsed into the TailoredCV + PersonalInfo schema.

    Used as the canonical intermediate model by both `ats_checker_agent` (parsed from PDF)
    and `cv_agent` (built directly from `TailoredCV` + `PersonalInfo`) before grading.
    Unavailable sections are kept as None or [].
    """

    personal_info: PersonalInfo = Field(
        default_factory=PersonalInfo,
        description="Contact info; keep LinkedIn/GitHub/Portfolio labels or URLs in linkedin_url/portfolio_url",
    )
    professional_summary: str | None = Field(
        None,
        description="Summary/objective if present; null if absent",
    )
    work_experiences: list[TailoredExperience] = Field(
        default_factory=list,
        description="Work experiences with every role bullet sentence in `bullets`",
    )
    education: list[Education] = Field(
        default_factory=list,
        description="Education entries",
    )
    leadership_activities: list[LeadershipActivity] = Field(
        default_factory=list,
        description="Leadership, TA, org, or volunteer entries with bullets",
    )
    certifications: list[Certification] = Field(
        default_factory=list,
        description="Certifications and licenses",
    )
    projects: list[Project] = Field(
        default_factory=list,
        description="Projects with bullets merged into `description` to keep metrics",
    )
    skills: list[SkillCategory] = Field(
        default_factory=list,
        description="Grouped skills per category, or single category='Skills' if flat",
    )
    skills_are_categorized: bool = Field(
        default=False,
        description="True if grouped under 2+ named categories; False if flat or absent",
    )
    additional_sections: list[str] = Field(
        default_factory=list,
        description="Additional sections (Languages, Interests, Awards, Publications)",
    )
    detected_section_headings: list[str] = Field(
        default_factory=list,
        description="Verbatim section headings found in CV",
    )
    non_standard_headings: list[str] = Field(
        default_factory=list,
        description="Only informal headings (e.g. 'About Me', 'What I Did'); [] for standard ATS headings",
    )
    word_count: int = Field(
        default=0,
        description="Approximate total word count",
    )

    @classmethod
    def from_tailored_cv(
        cls,
        cv: TailoredCV,
        personal_info: PersonalInfo | None = None,
        fallback_name: str | None = None,
    ) -> "ParsedCVDocument":
        """Construct a ParsedCVDocument directly from a generated TailoredCV and PersonalInfo."""
        resolved_info = (
            personal_info.model_copy(deep=True) if personal_info is not None else PersonalInfo()
        )
        if not resolved_info.name and fallback_name:
            resolved_info.name = fallback_name

        headings: list[str] = []
        if cv.professional_summary:
            headings.append("Professional Summary")
        if cv.work_experiences:
            headings.append("Professional Experience")
        if cv.education:
            headings.append("Education")
        if cv.leadership_activities:
            headings.append("Leadership & Activity")
        if cv.certifications:
            headings.append("Certifications")
        if cv.projects:
            headings.append("Projects")
        if cv.skills:
            headings.append("Technical Skills")

        active_skill_cats = [c for c in cv.skills if c.items]
        is_categorized = len(active_skill_cats) >= 2 or (
            len(active_skill_cats) == 1
            and active_skill_cats[0].category.strip().lower() not in ("skills", "technical skills")
        )

        # Compute word count across structured fields
        text_parts: list[str] = []
        if resolved_info.name:
            text_parts.append(resolved_info.name)
        if resolved_info.other_url:
            text_parts.append(resolved_info.other_url)
        if cv.professional_summary:
            text_parts.append(cv.professional_summary)
        for exp in cv.work_experiences:
            text_parts.extend(filter(None, [exp.title, exp.company, exp.location, exp.start_date, exp.end_date]))
            text_parts.extend(exp.bullets)
        for edu in cv.education:
            text_parts.extend(filter(None, [edu.institution, edu.degree, edu.field, edu.gpa]))
            text_parts.extend(edu.relevant_coursework)
        for act in cv.leadership_activities:
            text_parts.extend(filter(None, [act.title, act.organization, act.location]))
            text_parts.extend(act.bullets)
        for cert in cv.certifications:
            text_parts.extend(filter(None, [cert.name, cert.issuer, cert.date, cert.url]))
        for proj in cv.projects:
            text_parts.extend(filter(None, [proj.name, proj.description, proj.url]))
            text_parts.extend(proj.technologies)
        for cat in active_skill_cats:
            text_parts.append(cat.category)
            text_parts.extend(cat.items)

        total_words = len(" ".join(text_parts).split())

        return cls(
            personal_info=resolved_info,
            professional_summary=cv.professional_summary,
            work_experiences=list(cv.work_experiences),
            education=list(cv.education),
            leadership_activities=list(cv.leadership_activities),
            certifications=list(cv.certifications),
            projects=list(cv.projects),
            skills=active_skill_cats,
            skills_are_categorized=is_categorized,
            additional_sections=[],
            detected_section_headings=headings,
            non_standard_headings=[],
            word_count=total_words,
        )


class ATSSectionScore(BaseModel):
    """Score and feedback for a single detected CV section."""

    section_name: str = Field(..., description="Canonical section name")
    score: int = Field(..., ge=0, le=100, description="Section score 0-100")
    present: bool = Field(..., description="Whether section is present")
    weight: float = Field(..., ge=0, le=1, description="Dynamic section weight (weights sum to 1.0)")
    feedback: str = Field(..., description="Qualitative strengths and exact gaps; if score <100, explain why points were deducted (no numbers/X/100)")
    suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable fixes; if score <95, MUST include >=1 concrete fix",
    )


class ATSKeywordAnalysis(BaseModel):
    """Keyword presence and optimization analysis."""

    detected_keywords: list[str] = Field(default_factory=list, description="Domain keywords found in CV")
    missing_common_keywords: list[str] = Field(default_factory=list, description="Absent domain keywords (never already present)")
    keyword_density_rating: str = Field(..., description="'Low', 'Adequate', or 'Strong'")


class ATSFormattingIssue(BaseModel):
    """A single formatting or structural issue detected in the CV."""

    issue: str = Field(..., description="Concrete formatting defect")
    severity: str = Field(..., description="'Low', 'Medium', or 'High'")
    suggestion: str = Field(..., description="Actionable fix")


class ATSCheckResult(BaseModel):
    """Complete ATS check result — structured output from the grading agent."""

    overall_score: int = Field(..., ge=0, le=100, description="Weighted overall score 0-100")
    candidate_level: str = Field(..., description="'Entry-Level', 'Mid-Level', 'Senior', or 'Executive'")
    target_role: str | None = Field(default=None, description="Evaluated target job role if specified")
    company_name: str | None = Field(default=None, description="Evaluated target company if specified")
    sections: list[ATSSectionScore] = Field(..., description="Scored breakdown of evaluated sections")
    keyword_analysis: ATSKeywordAnalysis
    formatting_issues: list[ATSFormattingIssue] = Field(default_factory=list, description="Concrete formatting defects ([] if clean)")
    strengths: list[str] = Field(default_factory=list, description="Evidence-grounded ATS strengths")
    improvements: list[str] = Field(default_factory=list, description="Verified high-priority improvements")
    summary: str = Field(..., description="2-3 sentence qualitative summary tailored to career level (no numbers/X/100)")
