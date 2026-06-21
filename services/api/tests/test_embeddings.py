"""Embedding provider tests (v0.3): determinism, dimension, fallback target."""

from __future__ import annotations

from app.embeddings import cosine, embed, get_embedding_provider
from app.embeddings.stub import StubEmbeddingProvider


def test_stub_embedding_is_deterministic():
    a = embed("I prefer enterprise-style architecture explanations.")
    b = embed("I prefer enterprise-style architecture explanations.")
    assert a == b


def test_stub_embedding_has_configured_dimension():
    provider = get_embedding_provider()
    vec = embed("hello world")
    assert len(vec) == provider.dim == 1536


def test_stub_embedding_is_l2_normalized():
    vec = StubEmbeddingProvider(1536).embed_text("dark mode dashboards")
    norm = sum(v * v for v in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_default_provider_is_stub_offline():
    # No API key configured in tests → deterministic stub, never a network call.
    assert get_embedding_provider().name == "stub"


def test_embed_batch_matches_single():
    texts = ["alpha beta", "gamma delta"]
    batch = StubEmbeddingProvider(64).embed_batch(texts)
    assert batch == [StubEmbeddingProvider(64).embed_text(t) for t in texts]


def test_related_text_more_similar_than_unrelated():
    base = embed("I prefer dark mode dashboards")
    related = embed("dark mode dashboards are my preference")
    unrelated = embed("the capital of France is Paris")
    assert cosine(base, related) > cosine(base, unrelated)
