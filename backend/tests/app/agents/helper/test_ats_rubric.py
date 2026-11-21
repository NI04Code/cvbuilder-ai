"""Unit tests for app.agents.helper.ats_rubric."""

from collections import OrderedDict
import re
from unittest.mock import MagicMock, patch

from app.agents.helper import ats_rubric
from app.schemas.ats_checker import ATSFormattingIssue, ATSSectionScore
from tests.conftest import make_ats_check_result, make_parsed_cv_doc


def test_section_level_and_text_helpers():
    assert ats_rubric._canonical_section_key("Contact Information") == "contact"
    assert ats_rubric._canonical_section_key("Professional Experience") == "experience"
    assert ats_rubric._canonical_section_key("Technical Skills") == "skills"
    assert ats_rubric._canonical_section_key("Leadership & Activity") == "leadership"

    assert ats_rubric._normalize_level("Junior Intern") == "Entry-Level"
    assert ats_rubric._normalize_level("VP Engineering") == "Executive"
    assert ats_rubric._normalize_level("Senior Staff") == "Senior"
    assert ats_rubric._normalize_level("Mid") == "Mid-Level"

    lines = ["SUMMARY", "Line 1", "EXPERIENCE", "Line 2"]
    assert ats_rubric._extract_section_lines(lines, [(0, "summary"), (2, "experience")], "summary") == ["Line 1"]

    count, pct = ats_rubric._count_quantified_bullets(
        ["Reduced latency by 40% in 2024.", "Collaborated with team."]
    )
    assert count == 1 and pct == 50

    assert ats_rubric.normalize_cv_text("Hello\xa0World\u20132024\n\n  Line 2 ") == "Hello World-2024\nLine 2"


def test_extract_facts_and_format_sheet():
    raw_cv = "\n".join(
        [
            "Alex Candidate",
            "Jakarta, Indonesia | alex@example.com | +1 555 010 9999 | https://linkedin.com/in/alex",
            "Professional Summary",
            "Backend engineer with Python expertise.",
            "Professional Experience",
            "- Improved throughput by 50% across 4 services.",
            "- Reduced errors by 30% using automated tests.",
            "Education",
            "B.S. Computer Science, GPA 3.8",
            "Technical Skills",
            "Languages: Python, SQL",
            "Frameworks: FastAPI, Docker",
        ]
    )
    facts = ats_rubric.extract_cv_facts(raw_cv)
    assert facts["has_email"] is True
    assert facts["has_phone"] is True
    assert facts["has_linkedin_or_portfolio"] is True
    assert facts["uses_standard_headings"] is True
    assert facts["skills_categorized"] is True
    assert facts["quantified_pct"] == 100

    doc = make_parsed_cv_doc()
    doc_facts = ats_rubric.extract_facts_from_parsed_cv(doc)
    assert doc_facts["has_experience"] is True
    sheet = ats_rubric.format_cv_fact_sheet(doc_facts)
    assert "VERIFIED DOCUMENT FACT SHEET" in sheet
    assert "[PRESENT / VERIFIED]" in sheet


def test_false_positive_pruning_and_score_normalization():
    doc = make_parsed_cv_doc()
    facts = ats_rubric.extract_facts_from_parsed_cv(doc)
    res = make_ats_check_result(
        candidate_level="Mid",
        formatting_issues=[
            ATSFormattingIssue(
                issue="Non-standard headings detected",
                severity="Low",
                suggestion="Rename section headings.",
            )
        ],
        improvements=["Add your LinkedIn URL.", "Keep Kubernetes experience visible."],
        sections=[
            ATSSectionScore(
                section_name="Contact Information",
                score=70,
                present=True,
                weight=0.1,
                feedback="Missing LinkedIn URL.",
                suggestions=["Add LinkedIn link."],
            ),
            ATSSectionScore(
                section_name="Work Experience",
                score=80,
                present=True,
                weight=0.4,
                feedback="Solid experience.",
                suggestions=["Add older metrics."],
            ),
            ATSSectionScore(
                section_name="Formatting",
                score=80,
                present=True,
                weight=0.1,
                feedback="Standard headings used.",
                suggestions=[],
            ),
            ATSSectionScore(
                section_name="Certifications",
                score=0,
                present=False,
                weight=0.05,
                feedback="Absent",
                suggestions=[],
            ),
        ],
    )
    res.keyword_analysis.missing_common_keywords = ["Python", "Go"]

    assert ats_rubric._is_false_positive_text("Missing LinkedIn link", ats_rubric._build_false_positive_patterns(facts))
    cleaned = ats_rubric._clean_prose_false_positives(
        "Missing LinkedIn URL. Strong backend experience.",
        ats_rubric._build_false_positive_patterns(facts),
        "Fallback.",
    )
    assert "Strong backend experience." in cleaned

    items = ["Add metrics"]
    ats_rubric._append_unique_if_missing(items, "Add metrics now", "metric")
    assert len(items) == 1

    scored = ats_rubric.normalize_and_score_ats_result(
        res, normalized_text=str(facts["searchable_text"]), facts=facts
    )
    assert scored.candidate_level == "Mid-Level"
    assert "Python" not in scored.keyword_analysis.missing_common_keywords
    assert "Go" in scored.keyword_analysis.missing_common_keywords
    assert all(s.section_name != "Certifications" for s in scored.sections)
    assert abs(sum(s.weight for s in scored.sections) - 1.0) < 1e-3
    assert 0 <= scored.overall_score <= 100


def test_cache_and_llm_wrappers(monkeypatch):
    cache: OrderedDict = OrderedDict()
    doc = make_parsed_cv_doc()
    ats_rubric._cache_set(cache, "k1", doc)
    hit = ats_rubric._cache_get(cache, "k1")
    assert hit is not None and hit is not doc

    monkeypatch.setattr(ats_rubric, "_PARSE_CACHE", OrderedDict())
    monkeypatch.setattr(ats_rubric, "_ATS_CACHE", OrderedDict())

    mock_parse_llm = MagicMock()
    mock_parse_llm.invoke.return_value = make_parsed_cv_doc()
    mock_grade_llm = MagicMock()
    mock_grade_llm.invoke.return_value = make_ats_check_result()

    with patch(
        "app.agents.helper.ats_rubric.get_structured_llm",
        side_effect=[mock_parse_llm, mock_grade_llm],
    ):
        parsed = ats_rubric.parse_cv_to_structured("Alex\nhttps://linkedin.com/in/alex\nPython")
        parsed_cached = ats_rubric.parse_cv_to_structured("Alex\nhttps://linkedin.com/in/alex\nPython")
        graded = ats_rubric.grade_parsed_cv(parsed, target_role="Backend Engineer")
        graded_cached = ats_rubric.grade_parsed_cv(parsed, target_role="Backend Engineer")

    assert mock_parse_llm.invoke.call_count == 1
    assert mock_grade_llm.invoke.call_count == 1
    assert parsed_cached.word_count == parsed.word_count
    assert graded_cached.overall_score == graded.overall_score
