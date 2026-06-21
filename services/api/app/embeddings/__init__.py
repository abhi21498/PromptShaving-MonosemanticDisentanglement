"""Embedding provider package (v0.3).

Public surface:
  * ``get_embedding_provider()`` — cached, settings-selected provider.
  * ``embed(text)`` / ``embed_batch(texts)`` — convenience wrappers.
  * ``cosine`` — shared similarity helper.
  * ``EmbeddingProvider`` — the Protocol providers satisfy.
"""

from __future__ import annotations

from functools import lru_cache

from .base import EmbeddingProvider, cosine
from .providers import OpenAIEmbeddingProvider, build_provider
from .stub import StubEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "StubEmbeddingProvider",
    "cosine",
    "embed",
    "embed_batch",
    "get_embedding_provider",
]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return build_provider()


def embed(text: str) -> list[float]:
    return get_embedding_provider().embed_text(text)


def embed_batch(texts: list[str]) -> list[list[float]]:
    return get_embedding_provider().embed_batch(texts)
