"""Unit tests for app.agents.resume_agent."""

from unittest.mock import patch

import pytest
from langgraph.graph import END

from app.agents.resume_agent import process_resume, router
from app.schemas.profile import PersonalInfo, ResumeProfile
from tests.conftest import make_profile


def test_resume_agent_router():
    assert router({"error": "err", "raw_text": "abc"}) == END
    assert router({"error": None, "raw_text": ""}) == END
    assert router({"error": None, "raw_text": "valid text"}) == "parse_with_llm"


@pytest.mark.asyncio
async def test_process_resume_invokes_graph():
    parsed = ResumeProfile(personal_info=PersonalInfo(name="Alex"), summary="Dev")
    with patch(
        "app.agents.resume_agent.resume_parser_app.invoke",
        return_value={"raw_text": "raw", "parsed_profile": parsed, "error": None},
    ):
        out = await process_resume("/tmp/resume.pdf")

    assert out == {"raw_text": "raw", "profile": parsed, "error": None}
