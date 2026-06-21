"""Optional network embedding providers + provider selection.

Rules (v0.3):
  * Tests and offline runs never require a real key — selection falls back to the
    deterministic stub whenever a provider is unconfigured or unavailable.
  * A configured provider that raises at call time degrades to the stub per call
    (invariant #4), so a flaky embeddings API never blocks the read path.
"""

from __future__ import annotations

from ..core.config import get_settings
from ..core.logging import get_logger
from .stub import StubEmbeddingProvider

logger = get_logger("memoryops.embeddings")


class OpenAIEmbeddingProvider:
    """OpenAI embeddings, used only when ``OPENAI_API_KEY`` is set.

    Imports the ``openai`` SDK lazily so the package imports cleanly without it.
    Pads/truncates to ``dim`` so the stored vector always matches the column
    dimension regardless of model.
    """

    name = "openai"

    def __init__(self, api_key: str, model: str, dim: int = 1536) -> None:
        self._api_key = api_key
        self._model = model
        self.dim = dim
        self._fallback = StubEmbeddingProvider(dim)

    def _client(self):  # pragma: no cover - needs the openai package + key
        from openai import OpenAI

        return OpenAI(api_key=self._api_key)

    def _fit(self, vec: list[float]) -> list[float]:
        if len(vec) == self.dim:
            return vec
        if len(vec) > self.dim:
            return vec[: self.dim]
        return vec + [0.0] * (self.dim - len(vec))

    def embed_text(self, text: str) -> list[float]:
        try:  # pragma: no cover - exercised only with a real key
            resp = self._client().embeddings.create(model=self._model, input=text)
            return self._fit(list(resp.data[0].embedding))
        except Exception:  # noqa: BLE001 — degrade to deterministic stub
            logger.warning("openai embedding failed; using stub", extra={"event": "embed_fallback"})
            return self._fallback.embed_text(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:  # pragma: no cover - exercised only with a real key
            resp = self._client().embeddings.create(model=self._model, input=texts)
            return [self._fit(list(d.embedding)) for d in resp.data]
        except Exception:  # noqa: BLE001
            logger.warning("openai batch embedding failed; using stub",
                           extra={"event": "embed_fallback"})
            return self._fallback.embed_batch(texts)


def build_provider():
    """Select an embedding provider from settings, defaulting to the stub.

    ``MEMORYOPS_EMBEDDING_PROVIDER`` / ``embeddings_provider`` accepts
    ``stub`` (alias ``heuristic``) or ``openai``. ``openai`` without a key
    silently falls back to the stub so the app always starts.
    """
    settings = get_settings()
    dim = settings.embedding_dim
    provider = settings.embeddings_provider
    if provider == "openai" and settings.openai_api_key:
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dim=dim,
        )
    return StubEmbeddingProvider(dim)
