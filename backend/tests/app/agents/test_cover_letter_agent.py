"""Unit tests for app.agents.cover_letter_agent."""

from unittest.mock import patch

import pytest
from langgraph.graph import END

from app.agents.cover_letter_agent import (
    _cover_letter_router,
    process_cover_letter_generation,
)
from app.schemas.cover_letter import CoverLetterContent, CoverLetterGenerateRequest
from tests.conftest import make_job_requirements, make_profile_response


def test_cover_letter_router():
    assert _cover_letter_router({"error": "boom"}) == END
    assert _cover_letter_router({"error": None}) == "generate_cover_letter"


@pytest.mark.asyncio
async def test_process_cover_letter_generation_resolves_company():
    profile = make_profile_response()
    req = CoverLetterGenerateRequest(job_description="A" * 60, company_name=None)
    cl = CoverLetterContent(cover_letter_text="Dear Team,\n\n" + "Body " * 15)
    reqs = make_job_requirements(company="Resolved Corp")

    with patch(
        "app.agents.cover_letter_agent.cover_letter_app.invoke",
        return_value={"cover_letter": cl, "job_requirements": reqs, "error": None},
    ):
        out = await process_cover_letter_generation(profile, req, user_name="Alex")

    assert out["cover_letter"] is cl
    assert out["resolved_company"] == "Resolved Corp"
    assert out["error"] is None
