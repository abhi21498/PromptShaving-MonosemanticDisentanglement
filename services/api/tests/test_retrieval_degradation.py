"""Graceful degradation (invariant #4): embedding failure → keyword-only retrieval.

When the embedding provider raises, retrieval must not blow up or block the
response — it falls back to keyword ranking and reports retrieval_mode="fallback".
"""

from __future__ import annotations

import pytest

from app.schemas.memory import ChatRequest
from app.services.retriever import Retriever


def _chat(gateway, message, **kw):
    return gateway.handle_chat(
        ChatRequest(tenant_id="t1", user_id="u1", message=message, **kw), trace_id="test"
    )


@pytest.fixture
def boom_embeddings(monkeypatch):
    def _raise(_text):
        raise RuntimeError("embedding backend unavailable")

    # Patch the symbol the retriever actually calls.
    monkeypatch.setattr("app.services.retriever.embed", _raise)


def test_embedding_failure_degrades_to_keyword(gateway, boom_embeddings):
    _chat(gateway, "Remember that I prefer dark mode dashboards.")
    resp = _chat(gateway, "Which dashboard theme do I like?")
    # Response still produced; keyword path still finds the memory.
    assert resp.retrieval_mode == "fallback"
    assert any("dark mode" in u.content.lower() for u in resp.used_memories)


def test_fallback_marks_vector_similarity_zero(repo, gateway, boom_embeddings):
    _chat(gateway, "I'm building MemoryOps AI, a memory governance layer.")
    resp = _chat(gateway, "What is MemoryOps AI?")
    assert resp.retrieval_mode == "fallback"
    for u in resp.used_memories:
        assert u.score_breakdown["vector_similarity"] == 0.0


def test_retriever_returns_result_object(repo):
    r = Retriever(repo)
    result = r.retrieve("t1", "u1", "anything")
    assert hasattr(result, "candidates")
    assert hasattr(result, "mode")
