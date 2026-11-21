"""Unit tests for app.agents.ats_checker_agent."""

from unittest.mock import patch

import pytest
from langgraph.graph import END

from app.agents.ats_checker_agent import check_cv_ats, grade_router, parse_router
from tests.conftest import make_ats_check_result, make_parsed_cv_doc


def test_ats_checker_routers():
    assert parse_router({"error": "bad", "raw_text": "x"}) == END
    assert parse_router({"error": None, "raw_text": ""}) == END
    assert parse_router({"error": None, "raw_text": "hello"}) == "parse_cv"

    assert grade_router({"error": "bad", "parsed_cv": make_parsed_cv_doc()}) == END
    assert grade_router({"error": None, "parsed_cv": None}) == END
    assert grade_router({"error": None, "parsed_cv": make_parsed_cv_doc()}) == "grade_cv"


@pytest.mark.asyncio
async def test_check_cv_ats_invokes_graph():
    expected = make_ats_check_result()
    with patch(
        "app.agents.ats_checker_agent.ats_checker_app.invoke",
        return_value={"result": expected, "error": None},
    ) as mock_invoke:
        out = await check_cv_ats(b"%PDF-1.4", target_role="  Backend Engineer  ")

    assert out == {"result": expected, "error": None}
    assert mock_invoke.call_args.args[0]["target_role"] == "Backend Engineer"
