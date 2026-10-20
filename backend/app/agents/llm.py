"""Centralized LLM factory with dynamic model fallback support for agents."""

import logging
from typing import Type, TypeVar
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import Runnable

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def get_llm(
    temperature: float = 0.0,
    primary_model: str | None = None,
    fallback_models: list[str] | None = None,
) -> Runnable:
    """
    Returns an LLM runnable with automatic dynamic fallback to other frontier models
    if the primary model encounters rate limits (HTTP 429) or token/quota exhaustion.
    """
    primary = primary_model or settings.gemini_model
    fallbacks = (
        fallback_models
        if fallback_models is not None
        else settings.gemini_fallback_models
    )

    primary_llm = ChatGoogleGenerativeAI(
        model=primary,
        temperature=temperature,
        google_api_key=settings.google_api_key,
    )

    if not fallbacks:
        return primary_llm

    fallback_llms = [
        ChatGoogleGenerativeAI(
            model=m,
            temperature=temperature,
            google_api_key=settings.google_api_key,
        )
        for m in fallbacks
        if m != primary
    ]

    if not fallback_llms:
        return primary_llm

    logger.debug(
        f"Configured LLM primary={primary} with fallbacks={[m for m in fallbacks if m != primary]}"
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
    with automatic dynamic fallback to other frontier models on rate limit or token exhaustion.
    """
    primary = primary_model or settings.gemini_model
    fallbacks = (
        fallback_models
        if fallback_models is not None
        else settings.gemini_fallback_models
    )

    primary_llm = ChatGoogleGenerativeAI(
        model=primary,
        temperature=temperature,
        google_api_key=settings.google_api_key,
    ).with_structured_output(schema)

    if not fallbacks:
        return primary_llm

    fallback_llms = [
        ChatGoogleGenerativeAI(
            model=m,
            temperature=temperature,
            google_api_key=settings.google_api_key,
        ).with_structured_output(schema)
        for m in fallbacks
        if m != primary
    ]

    if not fallback_llms:
        return primary_llm

    logger.debug(
        f"Configured structured LLM ({schema.__name__}) primary={primary} with fallbacks={[m for m in fallbacks if m != primary]}"
    )
    return primary_llm.with_fallbacks(fallback_llms)
