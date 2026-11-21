"""Unit tests for app.agents.node.cover_letter_generation_node."""

from unittest.mock import MagicMock, patch

from app.agents.node.cover_letter_generation_node import (
    _normalize_cover_letter_text,
    generate_cover_letter_node,
)
from app.schemas.cover_letter import CoverLetterContent, CoverLetterGenerateRequest
from tests.conftest import make_job_requirements, make_profile_response


def test_normalize_cover_letter_text():
    raw = "Dear **Team**,\r\n\r\n\r\nExcited to apply.\r\n\r\nSincerely,\nAlex"
    assert _normalize_cover_letter_text(raw) == "Dear Team,\n\nExcited to apply.\n\nSincerely,\nAlex"


def test_generate_cover_letter_node():
    profile = make_profile_response()
    req = CoverLetterGenerateRequest(job_description="A" * 60, job_title="Backend Eng")
    reqs = make_job_requirements()

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = CoverLetterContent(
        cover_letter_text="Dear **Hiring Manager**,\n\n" + "Strong Python skills. " * 6
    )

    with patch("app.agents.node.cover_letter_generation_node.get_structured_llm", return_value=mock_llm):
        out = generate_cover_letter_node(
            {"profile": profile, "request": req, "job_requirements": reqs}
        )
    assert "**" not in out["cover_letter"].cover_letter_text

    mock_llm.invoke.side_effect = RuntimeError("timeout")
    with patch("app.agents.node.cover_letter_generation_node.get_structured_llm", return_value=mock_llm):
        err = generate_cover_letter_node({"profile": profile, "request": req})
    assert "Failed to generate cover letter" in err["error"]
