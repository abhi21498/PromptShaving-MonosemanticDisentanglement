"""Provider registry — settings-driven LLM provider selection (v0.4).

Mirrors the embedding-provider pattern (ADR-006): selection defaults to the
deterministic ``StubProvider`` and falls back to it whenever a networked provider
is unconfigured (no API key). This guarantees the app always starts and tests
never require a real key. ``MEMORYOPS_LLM_PROVIDER`` is the public knob; the
legacy ``heuristic`` value is treated as an alias for ``stub``.
"""

from __future__ import annotations

from functools import lru_cache

from ..core.config import Settings, get_settings
from ..core.logging import get_logger
from .anthropic_provider import AnthropicProvider
from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider
from .stub_provider import StubProvider

logger = get_logger("memoryops.llm")


def build_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Select an LLM provider from settings, defaulting to the stub.

    A networked provider without its API key silently degrades to the stub so the
    system never hard-fails on a missing secret (invariant #4).
    """
    settings = settings or get_settings()
    provider = settings.llm_provider
    timeout = settings.llm_timeout_seconds
    retries = settings.llm_max_retries

    if provider == "openai" and settings.openai_api_key:
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout=timeout,
            max_retries=retries,
        )
    if provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            timeout=timeout,
            max_retries=retries,
        )
    if provider == "gemini" and settings.gemini_api_key:
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout=timeout,
            max_retries=retries,
        )
    if provider in ("openai", "anthropic", "gemini"):
        logger.warning(
            "llm provider selected without an API key; using stub",
            extra={"event": "llm_provider_call", "provider": "stub", "fallback": True},
        )
    return StubProvider()


@lru_cache
def get_llm_provider() -> LLMProvider:
    return build_llm_provider()
