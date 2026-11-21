"""Unit tests for app.agents.node.pdf_extract_node."""

from unittest.mock import MagicMock, patch

from app.agents.node.pdf_extract_node import (
    _extract_from_doc,
    extract_ats_pdf_text_node,
    extract_resume_pdf_text_node,
)


def _mock_doc(text: str, links: list[dict] | None = None):
    page = MagicMock()
    page.get_text.return_value = text
    page.get_links.return_value = links or []
    doc = MagicMock()
    doc.__iter__.return_value = [page]
    doc.__enter__.return_value = doc
    doc.__exit__.return_value = False
    return doc


def test_extract_from_doc_and_nodes():
    doc = _mock_doc(
        "Alex Candidate",
        links=[
            {"uri": "https://github.com/alex"},
            {"uri": "mailto:alex@example.com"},
        ],
    )
    out = _extract_from_doc(doc, sort_order=True, include_links=True)
    assert "Alex Candidate" in out
    assert "Embedded Links: https://github.com/alex" in out
    assert "mailto:" not in out

    with patch("app.agents.node.pdf_extract_node.fitz.open", return_value=_mock_doc("Resume text")):
        res = extract_resume_pdf_text_node({"file_path": "/tmp/r.pdf"})
    assert res["raw_text"] == "Resume text"

    with patch("app.agents.node.pdf_extract_node.fitz.open", return_value=_mock_doc("   ")):
        empty = extract_resume_pdf_text_node({"file_path": "/tmp/r.pdf"})
    assert "Could not extract text" in empty["error"]

    with patch("app.agents.node.pdf_extract_node.fitz.open", return_value=_mock_doc("ATS text")):
        ats_ok = extract_ats_pdf_text_node({"file_bytes": b"%PDF-1.4"})
    assert "ATS text" in ats_ok["raw_text"]

    with patch("app.agents.node.pdf_extract_node.fitz.open", side_effect=RuntimeError("corrupt")):
        ats_err = extract_ats_pdf_text_node({"file_bytes": b"bad"})
    assert "Failed to read PDF" in ats_err["error"]
