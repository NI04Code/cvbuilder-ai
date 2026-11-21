"""Unit tests for app.agents.helper.llm_factory."""

from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from app.agents.helper import llm_factory
from app.core import settings


class _DummySchema(BaseModel):
    value: str


def test_create_chat_groq_and_build_structured_groq(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_timeout_seconds", 30.0)
    monkeypatch.setattr(settings, "llm_max_retries", 1)

    with patch("app.agents.helper.llm_factory.ChatGroq") as mock_groq_cls:
        llm_factory._create_chat_groq("openai/gpt-oss-120b", temperature=0.1)
        kwargs = mock_groq_cls.call_args.kwargs
        assert kwargs["timeout"] == 30.0
        assert kwargs["max_retries"] == 1
        assert kwargs["reasoning_effort"] == "low"

        mock_llm = MagicMock()
        mock_groq_cls.return_value = mock_llm
        llm_factory._build_structured_groq("openai/gpt-oss-120b", _DummySchema, 0.0)
        mock_llm.with_structured_output.assert_called_with(
            _DummySchema, method="json_schema", strict=True
        )

        mock_llm.reset_mock()
        llm_factory._build_structured_groq("qwen/qwen3.8-27b", _DummySchema, 0.0)
        mock_llm.with_structured_output.assert_called_with(_DummySchema)


def test_get_llm_and_get_structured_llm_fallbacks():
    primary = MagicMock()
    fallback = MagicMock()
    primary.with_fallbacks.return_value = "chained"

    with patch(
        "app.agents.helper.llm_factory._create_chat_groq",
        side_effect=[primary, fallback],
    ):
        res = llm_factory.get_llm(
            primary_model="m1",
            fallback_models=["m1", "m2"],
        )
    assert res == "chained"
    primary.with_fallbacks.assert_called_once_with([fallback])

    with patch(
        "app.agents.helper.llm_factory._create_chat_groq",
        return_value=primary,
    ):
        assert llm_factory.get_llm(primary_model="m1", fallback_models=[]) is primary

    s_primary = MagicMock()
    s_fallback = MagicMock()
    s_primary.with_fallbacks.return_value = "s_chained"
    with patch(
        "app.agents.helper.llm_factory._build_structured_groq",
        side_effect=[s_primary, s_fallback],
    ):
        s_res = llm_factory.get_structured_llm(
            _DummySchema,
            primary_model="m1",
            fallback_models=["m2"],
        )
    assert s_res == "s_chained"
