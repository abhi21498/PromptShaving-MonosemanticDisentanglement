"""Embedding provider interface (v0.3).

A synchronous Protocol on purpose: the MemoryOps read path (retriever → ranker →
composer → gateway → FastAPI routes) is synchronous end-to-end, so the embedding
boundary stays sync to read like the surrounding code and avoid a broad rewrite.
Real network providers do their I/O inside ``embed_text`` and degrade to the
deterministic stub on any failure (invariant #4, graceful degradation).

Swapping the vector backend later (Qdrant/Weaviate/Pinecone) does not touch this
interface — see ADR-006.
"""

from __future__ import annotations

import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Produces fixed-dimension embeddings for text."""

    name: str
    dim: int

    def embed_text(self, text: str) -> list[float]:
        """Embed a single string into a ``dim``-length vector."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed many strings; order-preserving."""
        ...


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity, safe on empty/mismatched/zero vectors (returns 0.0)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
