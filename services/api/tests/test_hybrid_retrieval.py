"""Hybrid retrieval tests (v0.3): score breakdown, mode, keyword + vector signals."""

from __future__ import annotations

from app.schemas.memory import ChatRequest

_BREAKDOWN_KEYS = {
    "vector_similarity",
    "keyword_score",
    "importance_score",
    "confidence",
    "recency",
    "reinforcement",
}


def _chat(gateway, message, **kw):
    return gateway.handle_chat(
        ChatRequest(tenant_id="t1", user_id="u1", message=message, **kw), trace_id="test"
    )


def test_score_breakdown_present(gateway):
    _chat(gateway, "Remember that I prefer dark mode dashboards.")
    resp = _chat(gateway, "Which dashboard theme do I like?")
    assert resp.used_memories
    for u in resp.used_memories:
        assert _BREAKDOWN_KEYS <= set(u.score_breakdown)
        # Components are normalized signals in [0, 1].
        assert all(0.0 <= v <= 1.0 for v in u.score_breakdown.values())


def test_default_mode_is_hybrid(gateway):
    _chat(gateway, "Remember that I prefer dark mode dashboards.")
    resp = _chat(gateway, "Which dashboard theme do I like?")
    assert resp.retrieval_mode == "hybrid"


def test_keyword_retrieval_catches_exact_project_name(gateway):
    _chat(gateway, "I'm building MemoryOps AI, an enterprise memory governance layer.")
    resp = _chat(gateway, "What is MemoryOps AI?")
    assert any("memoryops ai" in u.content.lower() for u in resp.used_memories)
    top = resp.used_memories[0]
    assert top.score_breakdown["keyword_score"] > 0.0


def test_used_memory_carries_type_and_source(gateway):
    _chat(gateway, "Remember that I prefer dark mode dashboards.")
    resp = _chat(gateway, "Which dashboard theme do I like?")
    u = resp.used_memories[0]
    assert u.memory_type is not None
    assert u.source is not None
