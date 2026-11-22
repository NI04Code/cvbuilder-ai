"""Unit tests for app.agents.node.cold_email_generation_node."""

from unittest.mock import MagicMock, patch

from app.agents.node.cold_email_generation_node import (
    _normalize_cold_email_text,
    generate_cold_email_node,
)
from app.schemas.cold_email import ColdEmailContent, ColdEmailGenerateRequest
from tests.conftest import make_job_requirements, make_profile_response


def test_normalize_cold_email_text():
    raw = "Hi **Sarah**,\r\n\r\n\r\nStrong hook here.\r\n\r\nBest,\nAlex"
    assert _normalize_cold_email_text(raw) == "Hi Sarah,\n\nStrong hook here.\n\nBest,\nAlex"


def test_generate_cold_email_node_uses_recruiter_name_and_handles_errors():
    profile = make_profile_response()
    req = ColdEmailGenerateRequest(
        job_description="A" * 60,
        job_title="Backend Engineer",
        company_name="Acme Corp",
        recruiter_name="Sarah Jenkins",
    )
    reqs = make_job_requirements()

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = ColdEmailContent(
        subject="**35% latency drop** — Backend Engineer fit",
        email_body="Hi **Sarah**,\n\n" + "Saw Acme Corp is scaling Python APIs. " * 4,
    )

    with patch(
        "app.agents.node.cold_email_generation_node.get_structured_llm",
        return_value=mock_llm,
    ):
        out = generate_cold_email_node(
            {"profile": profile, "request": req, "job_requirements": reqs}
        )

    assert "**" not in out["cold_email"].subject
    assert "**" not in out["cold_email"].email_body
    system_prompt = mock_llm.invoke.call_args.args[0][0].content
    assert "Sarah Jenkins" in system_prompt

    mock_llm.invoke.side_effect = RuntimeError("timeout")
    with patch(
        "app.agents.node.cold_email_generation_node.get_structured_llm",
        return_value=mock_llm,
    ):
        err = generate_cold_email_node({"profile": profile, "request": req})
    assert "Failed to generate cold email" in err["error"]
