"""Back-compat shim — embedding logic now lives in ``app.embeddings`` (v0.3).

The provider package is the source of truth. These re-exports keep existing
imports (``from ..core.embeddings import cosine, embed``) working while callers
migrate. New code should import from ``app.embeddings`` directly.
"""

from __future__ import annotations

from ..embeddings import cosine, embed, embed_batch, get_embedding_provider
from ..embeddings.stub import StubEmbeddingProvider


def heuristic_embedding(text: str, dim: int) -> list[float]:
    """Deterministic stub embedding (kept for back-compat callers/tests)."""
    return StubEmbeddingProvider(dim).embed_text(text)


__all__ = [
    "cosine",
    "embed",
    "embed_batch",
    "get_embedding_provider",
    "heuristic_embedding",
]
