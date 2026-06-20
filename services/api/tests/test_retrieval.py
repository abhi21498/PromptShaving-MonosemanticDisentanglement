"""Read path (Phase 2): relevant memory retrieved, irrelevant stays out."""

from __future__ import annotations

from app.schemas.memory import ChatRequest


def _chat(gateway, message, **kw):
    return gateway.handle_chat(
        ChatRequest(tenant_id="t1", user_id="u1", message=message, **kw), trace_id="test"
    )


def test_relevant_memory_is_used(gateway):
    _chat(gateway, "Remember that I prefer enterprise-style architecture explanations.")
    resp = _chat(gateway, "How should I explain my architecture style?")
    assert resp.used_memories
    assert any("enterprise" in u.content.lower() for u in resp.used_memories)


def test_deleted_memory_not_used_in_context(gateway, repo):
    _chat(gateway, "Remember that I prefer dark mode dashboards.")
    mem = repo.list_memories("t1", "u1")[0]
    repo.soft_delete("t1", "u1", mem.id)
    resp = _chat(gateway, "What dashboard mode do I like?")
    assert all(u.memory_id != mem.id for u in resp.used_memories)


def test_eval_harness_runs(gateway):
    from app.services.eval_harness import run_evals

    report = run_evals()
    assert report.total > 0
    # No critical invariant case should fail.
    critical = {"block", "deleted", "isolation", "temporary"}
    for r in report.results:
        if r.kind in critical:
            assert r.passed, f"critical case failed: {r.id} — {r.detail}"
