"""Unit tests for app.schemas.ats_checker."""

from app.schemas.ats_checker import ParsedCVDocument
from app.schemas.cv import SkillCategory
from tests.conftest import make_personal_info, make_tailored_cv


def test_parsed_cv_document_from_tailored_cv():
    cv = make_tailored_cv(
        skills=[
            SkillCategory(category="Languages", items=["Python"]),
            SkillCategory(category="Cloud", items=["Docker"]),
        ]
    )
    pi = make_personal_info(name="")
    doc = ParsedCVDocument.from_tailored_cv(cv, pi, fallback_name="Fallback Name")

    assert doc.personal_info.name == "Fallback Name"
    assert doc.skills_are_categorized is True
    assert "Professional Experience" in doc.detected_section_headings
    assert "Technical Skills" in doc.detected_section_headings
    assert doc.word_count > 0
