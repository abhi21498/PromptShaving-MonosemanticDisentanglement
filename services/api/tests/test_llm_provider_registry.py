"""Provider registry: default is the stub, networked providers degrade safely.

No test here requires a real API key (invariant for v0.4): an unconfigured
provider must fall back to the deterministic stub so the app always starts.
"""

from __future__ import annotations

from app.core.config import Settings
from app.llm import StubProvider, build_llm_provider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.openai_provider import OpenAIProvider


def test_default_provider_is_stub() -> None:
    provider = build_llm_provider(Settings(llm_provider="stub"))
    assert isinstance(provider, StubProvider)
    assert provider.name == "stub"


def test_heuristic_alias_resolves_to_stub() -> None:
    assert isinstance(build_llm_provider(Settings(llm_provider="heuristic")), StubProvider)


def test_networked_provider_without_key_falls_back_to_stub() -> None:
    for name in ("openai", "anthropic", "gemini"):
        provider = build_llm_provider(Settings(llm_provider=name))  # no key set
        assert isinstance(provider, StubProvider), name


def test_networked_provider_selected_when_key_present() -> None:
    assert isinstance(
        build_llm_provider(Settings(llm_provider="openai", openai_api_key="sk-x")),
        OpenAIProvider,
    )
    assert isinstance(
        build_llm_provider(Settings(llm_provider="anthropic", anthropic_api_key="ak-x")),
        AnthropicProvider,
    )
    assert isinstance(
        build_llm_provider(Settings(llm_provider="gemini", gemini_api_key="gk-x")),
        GeminiProvider,
    )


def test_provider_satisfies_protocol() -> None:
    # The selected provider exposes the LLMProvider surface used by the layer.
    provider = build_llm_provider(Settings(llm_provider="stub"))
    assert callable(provider.complete)
    assert hasattr(provider, "name")
