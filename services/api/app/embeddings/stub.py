"""Deterministic stub embedding provider (no API key, test-safe).

A hashed bag-of-words projected into ``dim`` then L2-normalized. Deterministic for
the same text, needs no network, and yields meaningful cosine similarity for
keyword/semantic overlap — enough to exercise pgvector retrieval and evals
offline. This is the default provider and the universal fallback target.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class StubEmbeddingProvider:
    name = "stub"

    def __init__(self, dim: int = 1536) -> None:
        self.dim = dim

    def embed_text(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _tokens(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)  # noqa: S324 — non-crypto use
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]
