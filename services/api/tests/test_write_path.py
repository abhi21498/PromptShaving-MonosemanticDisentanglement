"""Phase 1 write path: capture, classify, score, provenance, decisions."""

from __future__ import annotations

from app.schemas.memory import ChatRequest, Decision, MemoryType, Status


def _chat(gateway, message, **kw):
    return gateway.handle_chat(
        ChatRequest(tenant_id="t1", user_id="u1", message=message, **kw), trace_id="test"
    )


def test_explicit_preference_is_saved(gateway, repo):
    resp = _chat(gateway, "Remember that I prefer enterprise-style explanations with no emojis.")
    decisions = [c.decision for c in resp.candidate_memories]
    assert Decision.SAVE in decisions
    rows = repo.list_memories("t1", "u1")
    assert len(rows) == 1
    assert rows[0].status == Status.active
    assert rows[0].memory_type == MemoryType.procedural


def test_provenance_is_always_present(gateway, repo):
    _chat(gateway, "Remember that I work in fintech.")
    row = repo.list_memories("t1", "u1")[0]
    assert row.source is not None
    assert row.source.kind == "chat"
    assert row.source.excerpt  # the original message is preserved


def test_trivia_is_dropped(gateway, repo):
    resp = _chat(gateway, "The weather is nice today.")
    # Either no candidate extracted, or extracted then dropped — never stored.
    assert all(c.decision != Decision.SAVE for c in resp.candidate_memories)
    assert repo.list_memories("t1", "u1") == []


def test_audit_event_written_on_save(gateway, repo):
    resp = _chat(gateway, "Remember that I prefer dark mode.")
    assert resp.audit_event_ids
    audit = repo.list_audit("t1", "u1")
    assert any(e.action == "memory_created" for e in audit)


def test_duplicate_updates_instead_of_duplicating(gateway, repo):
    _chat(gateway, "Remember that I prefer dark mode.")
    _chat(gateway, "Remember that I prefer dark mode.")
    rows = repo.list_memories("t1", "u1")
    assert len(rows) == 1
    assert rows[0].reinforcement_count >= 1
