"""Unit tests for app.agents.cold_email_agent."""

from unittest.mock import patch

import pytest
from langgraph.graph import END

from app.agents.cold_email_agent import (
    _cold_email_router,
    process_cold_email_generation,
)
from app.schemas.cold_email import ColdEmailContent, ColdEmailGenerateRequest
from tests.conftest import make_job_requirements, make_profile_response


def test_cold_email_router():
    assert _cold_email_router({"error": "boom"}) == END
    assert _cold_email_router({"error": None}) == "generate_cold_email"


@pytest.mark.asyncio
async def test_process_cold_email_generation_resolves_company():
    profile = make_profile_response()
    req = ColdEmailGenerateRequest(
        job_description="A" * 60,
        company_name=None,
        recruiter_name="Sarah Jenkins",
    )
    email = ColdEmailContent(
        subject="Cut API latency 35% — Backend Engineer",
        email_body="Hi Sarah,\n\n" + "Strong hook and relevant metrics. " * 4,
    )
    reqs = make_job_requirements(company="Resolved Corp")

    with patch(
        "app.agents.cold_email_agent.cold_email_app.invoke",
        return_value={"cold_email": email, "job_requirements": reqs, "error": None},
    ):
        out = await process_cold_email_generation(profile, req, user_name="Alex")

    assert out["cold_email"] is email
    assert out["resolved_company"] == "Resolved Corp"
    assert out["error"] is None
