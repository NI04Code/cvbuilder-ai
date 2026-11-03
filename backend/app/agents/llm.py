"""Centralized LLM factory with dynamic model fallback support for agents."""

import logging
from typing import Type, TypeVar
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.runnables import Runnable

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Groq models that support native Structured Outputs (response_format: json_schema)
_JSON_SCHEMA_MODELS = (
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "moonshotai/kimi-k2-instruct-0905",
)


def _build_structured_groq(
    model: str,
    schema: Type[T],
    temperature: float,
) -> Runnable:
    """Create a structured-output ChatGroq runnable using json_schema (constrained decoding) when supported."""
    llm = ChatGroq(
        model=model,
        temperature=temperature,
        api_key=settings.groq_api_key,
    )
    if any(model.startswith(prefix) for prefix in _JSON_SCHEMA_MODELS):
        return llm.with_structured_output(schema, method="json_schema", strict=True)
    return llm.with_structured_output(schema)


def get_llm(
    temperature: float = 0.0,
    primary_model: str | None = None,
    fallback_models: list[str] | None = None,
) -> Runnable:
    """
    Returns an LLM runnable with automatic dynamic fallback to other Groq models
    if the primary model encounters rate limits (HTTP 429) or token/quota exhaustion.
    """
    primary = primary_model or settings.groq_model
    fallbacks = (
        fallback_models
        if fallback_models is not None
        else settings.groq_fallback_models
    )

    primary_llm = ChatGroq(
        model=primary,
        temperature=temperature,
        api_key=settings.groq_api_key,
    )

    if not fallbacks:
        return primary_llm

    fallback_llms = [
        ChatGroq(
            model=m,
            temperature=temperature,
            api_key=settings.groq_api_key,
        )
        for m in fallbacks
        if m != primary
    ]

    if not fallback_llms:
        return primary_llm

    logger.debug(
        f"Configured Groq LLM primary={primary} with fallbacks={[m for m in fallbacks if m != primary]}"
    )
    return primary_llm.with_fallbacks(fallback_llms)


def get_structured_llm(
    schema: Type[T],
    temperature: float = 0.0,
    primary_model: str | None = None,
    fallback_models: list[str] | None = None,
) -> Runnable:
    """
    Returns a structured-output LLM runnable bound to a Pydantic schema,
    with automatic dynamic fallback to other Groq models on rate limit or token exhaustion.
    """
    primary = primary_model or settings.groq_model
    fallbacks = (
        fallback_models
        if fallback_models is not None
        else settings.groq_fallback_models
    )

    primary_llm = _build_structured_groq(primary, schema, temperature)

    if not fallbacks:
        return primary_llm

    fallback_llms = [
        _build_structured_groq(m, schema, temperature)
        for m in fallbacks
        if m != primary
    ]

    if not fallback_llms:
        return primary_llm

    logger.debug(
        f"Configured structured Groq LLM ({schema.__name__}) primary={primary} with fallbacks={[m for m in fallbacks if m != primary]}"
    )
    return primary_llm.with_fallbacks(fallback_llms)
