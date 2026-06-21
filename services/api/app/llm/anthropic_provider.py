"""Anthropic Messages provider (v0.4).

Used only when ``ANTHROPIC_API_KEY`` is set and
``MEMORYOPS_LLM_PROVIDER=anthropic``. The ``anthropic`` SDK is imported lazily.
Any failure propagates as ``LLMUnavailableError`` and the caller degrades to the
deterministic heuristic. Defaults to a current Claude model.
"""

from __future__ import annotations

from .providers import BaseNetworkProvider


class AnthropicProvider(BaseNetworkProvider):
    name = "anthropic"

    def _invoke(self, *, system: str, user: str, task: str) -> str:  # pragma: no cover - needs key
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key, timeout=self._timeout)
        resp = client.messages.create(
            model=self._model,
            system=system,
            max_tokens=1024,
            temperature=0,
            messages=[{"role": "user", "content": user}],
        )
        # Concatenate text blocks from the response content.
        return "".join(getattr(block, "text", "") for block in resp.content)
