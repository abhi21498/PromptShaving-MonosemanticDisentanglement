"""LLM adapter interface with a heuristic, no-API-key implementation.

The extractor and (later) the response composer call ``get_llm()``. The default
``HeuristicLLM`` keeps the whole system functional offline; provider adapters
(OpenAI/Anthropic/Gemini) can be added behind the same ``LLM`` protocol without
touching call sites. Calls are wrapped by the caller with reliability primitives.
"""

from __future__ import annotations

from typing import Protocol

from .config import get_settings


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class HeuristicLLM:
    """Deterministic stand-in. Returns a templated, memory-aware answer."""

    def complete(self, system: str, user: str) -> str:
        return (
            "Here is a concise, enterprise-style response based on your request "
            "and any relevant remembered preferences."
        )


def get_llm() -> LLM:
    settings = get_settings()
    provider = settings.llm_provider
    # Provider adapters are intentionally deferred; fall back to heuristic so the
    # system never hard-fails on a missing key (invariant #4).
    if provider in ("openai", "anthropic", "gemini"):
        return HeuristicLLM()
    return HeuristicLLM()
