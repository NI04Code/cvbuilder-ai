"""Unit tests for app.utils.pdf_builder."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.utils import pdf_builder
from tests.conftest import make_personal_info, make_tailored_cv


def test_date_header_context_and_paragraph_helpers():
    assert pdf_builder._format_display_date("2024-03") == "Mar 2024"
    assert pdf_builder._format_display_date("2024-03-15") == "Mar 2024"
    assert pdf_builder._format_display_date("Present") == "Present"
    assert pdf_builder._format_display_date(None) is None

    pi = make_personal_info(
        other_url="https://github.com/alex",
        linkedin_url="https://linkedin.com/in/alex-very-long-profile-handle-exceeding-limit",
    )
    items = pdf_builder._build_header_items(pi)
    labels = [item["label"] for item in items]
    assert "LinkedIn" in labels
    assert "GitHub" in labels

    ctx = pdf_builder._prepare_cv_context(make_tailored_cv())
    assert ctx["work_experiences"][0]["start_date"] == "Jan 2022"

    paragraphs = pdf_builder._split_letter_paragraphs("Hello,\n\nLine 1\nLine 2\n\nSincerely,\nAlex")
    assert paragraphs == [["Hello,"], ["Line 1", "Line 2"], ["Sincerely,", "Alex"]]


def test_generate_cv_and_cover_letter_pdfs(tmp_path: Path):
    cv_out = tmp_path / "cv.pdf"
    cl_out = tmp_path / "cl.pdf"
    pi = make_personal_info()

    fake_doc = MagicMock()
    fake_doc.__len__.return_value = 1

    with patch("app.utils.pdf_builder._render_story_to_pdf_doc", return_value=fake_doc):
        assert pdf_builder.generate_cv_pdf(make_tailored_cv(), pi, str(cv_out)) == str(cv_out)
        assert (
            pdf_builder.generate_cover_letter_pdf(
                "Dear Team,\n\nParagraph.\n\nSincerely,\nAlex",
                pi,
                str(cl_out),
                job_title="Engineer",
                company_name="Acme",
            )
            == str(cl_out)
        )
    assert fake_doc.save.call_count == 2
    assert fake_doc.close.call_count == 2

    # Multi-page cover letter triggers preset stepping + page trim guard
    oversized_doc = MagicMock()
    oversized_doc.__len__.return_value = 2
    with patch("app.utils.pdf_builder._render_story_to_pdf_doc", return_value=oversized_doc):
        pdf_builder.generate_cover_letter_pdf("Long\n\nLetter", pi, str(cl_out))
    oversized_doc.delete_pages.assert_called_once_with(from_page=1, to_page=1)
