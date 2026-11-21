"""Unit tests for app.agents.node.job_analysis_node."""

from unittest.mock import MagicMock, patch

from app.agents.node.job_analysis_node import analyze_job_node
from app.schemas.document import JobTargetedRequest
from tests.conftest import make_job_requirements


def test_analyze_job_node():
    req = JobTargetedRequest(job_description="A" * 60, job_title="Backend Eng", company_name="Acme")
    reqs = make_job_requirements()
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = reqs

    with patch("app.agents.node.job_analysis_node.get_structured_llm", return_value=mock_llm):
        out = analyze_job_node({"request": req})
    assert out["job_requirements"] is reqs

    mock_llm.invoke.side_effect = RuntimeError("llm down")
    with patch("app.agents.node.job_analysis_node.get_structured_llm", return_value=mock_llm):
        err = analyze_job_node({"request": req})
    assert "Failed to analyze job description" in err["error"]
