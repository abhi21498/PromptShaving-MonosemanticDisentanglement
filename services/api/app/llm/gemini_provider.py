"""Google Gemini provider (v0.4).

Used only when ``GEMINI_API_KEY`` is set and ``MEMORYOPS_LLM_PROVIDER=gemini``.
The ``google-generativeai`` SDK is imported lazily. Any failure propagates as
``LLMUnavailableError`` and the caller degrades to the deterministic heuristic.
"""

from __future__ import annotations

from .providers import BaseNetworkProvider


class GeminiProvider(BaseNetworkProvider):
    name = "gemini"

    def _invoke(self, *, system: str, user: str, task: str) -> str:  # pragma: no cover - needs key
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self._model, system_instruction=system)
        resp = model.generate_content(
            user,
            generation_config={"temperature": 0},
            request_options={"timeout": self._timeout},
        )
        return resp.text or ""
