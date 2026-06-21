"""OpenAI chat-completions provider (v0.4).

Used only when ``OPENAI_API_KEY`` is set and ``MEMORYOPS_LLM_PROVIDER=openai``.
The ``openai`` SDK is imported lazily so the package imports without it. Any
failure propagates as ``LLMUnavailableError`` (via the base) and the caller
degrades to the deterministic heuristic.
"""

from __future__ import annotations

from .providers import BaseNetworkProvider


class OpenAIProvider(BaseNetworkProvider):
    name = "openai"

    def _invoke(self, *, system: str, user: str, task: str) -> str:  # pragma: no cover - needs key
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, timeout=self._timeout)
        resp = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            response_format={"type": "json_object"} if task != "general" else None,
        )
        return resp.choices[0].message.content or ""
