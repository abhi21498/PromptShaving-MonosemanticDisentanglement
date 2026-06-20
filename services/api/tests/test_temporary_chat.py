"""Temporary chat (invariant #6): no write, no read; degradation (#4)."""

from __future__ import annotations

from app.schemas.memory import ChatRequest


def test_temporary_chat_writes_nothing(gateway, repo):
    resp = gateway.handle_chat(
        ChatRequest(
            tenant_id="t1",
            user_id="u1",
            message="Remember that I like casual answers.",
            temporary_chat=True,
        ),
        trace_id="test",
    )
    assert resp.temporary_chat is True
    assert resp.candidate_memories == []
    assert repo.list_memories("t1", "u1", include_deleted=True) == []
    assert any(e.action == "temporary_chat_skipped" for e in repo.list_audit("t1", "u1"))


def test_temporary_chat_retrieves_nothing(gateway, repo):
    # Seed a normal memory first.
    gateway.handle_chat(
        ChatRequest(tenant_id="t1", user_id="u1", message="Remember I prefer dark mode."),
        trace_id="seed",
    )
    resp = gateway.handle_chat(
        ChatRequest(
            tenant_id="t1", user_id="u1", message="What do I prefer?", temporary_chat=True
        ),
        trace_id="test",
    )
    assert resp.used_memories == []


def test_memory_disabled_setting_bypasses_memory(gateway, repo):
    from app.db.entities import StoredSettings

    repo.upsert_settings(StoredSettings(tenant_id="t1", user_id="u1", memory_enabled=False))
    resp = gateway.handle_chat(
        ChatRequest(tenant_id="t1", user_id="u1", message="Remember I prefer dark mode."),
        trace_id="test",
    )
    assert resp.candidate_memories == []
    assert repo.list_memories("t1", "u1", include_deleted=True) == []
