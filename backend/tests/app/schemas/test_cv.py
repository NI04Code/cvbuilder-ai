"""Unit tests for app.schemas.cv."""

from app.schemas.cv import TailoredCV


def test_tailored_cv_normalizes_skills_and_section_order():
    cv = TailoredCV(
        skills=["Python", "FastAPI", " "],  # legacy flat list
        section_order=["skills", "education", "experience", "summary"],
        ats_score=82.5,
    )
    assert len(cv.skills) == 1
    assert cv.skills[0].category == "Technical Skills"
    assert cv.skills[0].items == ["Python", "FastAPI"]
    assert cv.section_order == [
        "summary",
        "education",
        "experience",
        "leadership",
        "certifications",
        "projects",
        "skills",
    ]
