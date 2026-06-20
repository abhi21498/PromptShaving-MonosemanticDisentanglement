"""Embedding adapter with a deterministic heuristic fallback.

The heuristic embedder is a hashed bag-of-words projected into ``embedding_dim``
then L2-normalized. It is deterministic (good for tests), needs no API key, and
gives meaningful cosine similarity for keyword overlap — enough to demonstrate
the read path. Swap in a real provider behind the same interface in Phase 4.
"""

from __future__ import annotations

import hashlib
import math
import re

from .config import get_settings

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def heuristic_embedding(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    for tok in _tokens(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)  # noqa: S324 — non-crypto use
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def embed(text: str) -> list[float]:
    settings = get_settings()
    dim = settings.embedding_dim
    if settings.embeddings_provider == "openai" and settings.openai_api_key:
        try:
            return _openai_embedding(text, dim)
        except Exception:  # noqa: BLE001 — degrade to heuristic
            return heuristic_embedding(text, dim)
    return heuristic_embedding(text, dim)


def _openai_embedding(text: str, dim: int) -> list[float]:  # pragma: no cover - needs key
    # Placeholder for the real provider call; kept import-light so the package
    # imports with no openai dependency installed.
    raise NotImplementedError("OpenAI embeddings not wired in Phase 1; using heuristic.")


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
