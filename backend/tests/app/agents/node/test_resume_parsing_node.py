"""Unit tests for app.agents.node.resume_parsing_node."""

from unittest.mock import MagicMock, patch

from app.agents.node.resume_parsing_node import parse_with_llm_node
from app.schemas.profile import PersonalInfo, ResumeProfile


def test_parse_with_llm_node():
    parsed = ResumeProfile(personal_info=PersonalInfo(name="Alex"), summary="Backend")
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = parsed

    with patch("app.agents.node.resume_parsing_node.get_structured_llm", return_value=mock_llm):
        out = parse_with_llm_node({"raw_text": "Alex Backend"})
    assert out["parsed_profile"] is parsed

    mock_llm.invoke.side_effect = RuntimeError("api error")
    with patch("app.agents.node.resume_parsing_node.get_structured_llm", return_value=mock_llm):
        err = parse_with_llm_node({"raw_text": "Alex Backend"})
    assert "Failed to parse resume with AI" in err["error"]
