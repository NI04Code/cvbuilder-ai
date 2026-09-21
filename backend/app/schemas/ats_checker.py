"""Pydantic schemas for the public ATS Checker feature."""

from pydantic import BaseModel, Field


class ATSSectionScore(BaseModel):
    """Score and feedback for a single detected CV section."""

    section_name: str = Field(
        ..., description="Name of the detected section (e.g., 'Work Experience', 'Skills')"
    )
    score: int = Field(
        ..., ge=0, le=100, description="Section score from 0 to 100"
    )
    present: bool = Field(
        ..., description="Whether this section was found in the CV"
    )
    weight: float = Field(
        ..., ge=0, le=1,
        description=(
            "How much this section matters for this specific CV's overall score, "
            "as a decimal between 0 and 1. All weights across sections must sum to 1.0. "
            "Assign weights dynamically based on what sections are present and the "
            "candidate's apparent career level."
        ),
    )
    feedback: str = Field(
        ..., description="Specific feedback explaining the score"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable improvement suggestions for this section",
    )


class ATSKeywordAnalysis(BaseModel):
    """Keyword presence and optimization analysis."""

    detected_keywords: list[str] = Field(
        default_factory=list,
        description="Industry-relevant keywords found in the CV",
    )
    missing_common_keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Common industry keywords that could strengthen the CV but are currently absent. "
            "Only suggest keywords relevant to the candidate's apparent field."
        ),
    )
    keyword_density_rating: str = Field(
        ...,
        description="Rating of keyword usage: 'Low', 'Adequate', or 'Strong'",
    )


class ATSFormattingIssue(BaseModel):
    """A single formatting or structural issue detected in the CV."""

    issue: str = Field(..., description="Description of the formatting problem")
    severity: str = Field(
        ..., description="Severity level: 'Low', 'Medium', or 'High'"
    )
    suggestion: str = Field(..., description="How to fix this issue")


class ATSCheckResult(BaseModel):
    """Complete ATS check result — structured output from the grading agent."""

    overall_score: int = Field(
        ..., ge=0, le=100,
        description=(
            "Weighted overall ATS compatibility score from 0 to 100. "
            "Computed as the weighted average of all section scores "
            "using each section's dynamic weight."
        ),
    )
    candidate_level: str = Field(
        ...,
        description=(
            "Detected career level of the candidate: "
            "'Entry-Level', 'Mid-Level', 'Senior', or 'Executive'. "
            "This determines how sections are weighted and whether "
            "missing optional sections are penalized."
        ),
    )
    sections: list[ATSSectionScore] = Field(
        ...,
        description=(
            "Scored breakdown by CV section. Only include sections that are "
            "detectable or contextually expected. For example, a senior candidate "
            "with 10+ years of work experience should NOT be penalized for omitting "
            "a Professional Summary if their experience section is strong."
        ),
    )
    keyword_analysis: ATSKeywordAnalysis
    formatting_issues: list[ATSFormattingIssue] = Field(default_factory=list)
    strengths: list[str] = Field(
        default_factory=list,
        description="Key strengths of the CV from an ATS perspective",
    )
    improvements: list[str] = Field(
        default_factory=list,
        description="Top priority improvements the candidate should make",
    )
    summary: str = Field(
        ...,
        description=(
            "2-3 sentence executive summary of the CV's ATS readiness, "
            "tailored to the candidate's detected career level."
        ),
    )
