"""Unit tests for app.agents.cv_agent."""

from unittest.mock import patch

import pytest
from langgraph.graph import END

from app.agents.cv_agent import process_cv_generation, router, score_router
from app.schemas.cv import CVGenerateRequest
from tests.conftest import make_job_requirements, make_profile_response, make_tailored_cv


def test_cv_agent_routers():
    assert router({"error": "err"}) == END
    assert router({"error": None}) == "generate_cv"

    assert score_router({"error": "err", "tailored_cv": make_tailored_cv()}) == END
    assert score_router({"error": None, "tailored_cv": None}) == END
    assert score_router({"error": None, "tailored_cv": make_tailored_cv()}) == "score_cv"


@pytest.mark.asyncio
async def test_process_cv_generation_resolves_company():
    profile = make_profile_response()
    req = CVGenerateRequest(job_description="A" * 60, company_name=None)
    cv = make_tailored_cv()
    reqs = make_job_requirements(company="Inferred Inc")

    with patch(
        "app.agents.cv_agent.cv_generator_app.invoke",
        return_value={"tailored_cv": cv, "job_requirements": reqs, "error": None},
    ):
        out = await process_cv_generation(profile, req, user_name="Alex")

    assert out["tailored_cv"] is cv
    assert out["resolved_company"] == "Inferred Inc"
    assert out["error"] is None
