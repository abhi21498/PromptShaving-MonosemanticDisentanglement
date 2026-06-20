"""Deletion guarantee (invariant #2): deleted memory is never retrieved."""

from __future__ import annotations

from app.schemas.memory import ChatRequest, Status


def _chat(gateway, message):
    return gateway.handle_chat(
        ChatRequest(tenant_id="t1", user_id="u1", message=message), trace_id="test"
    )


def test_deleted_memory_excluded_from_retrieval(gateway, repo):
    _chat(gateway, "Remember that I prefer dark mode dashboards.")
    mem = repo.list_memories("t1", "u1")[0]

    deleted = repo.soft_delete("t1", "u1", mem.id)
    assert deleted.status == Status.deleted
    assert deleted.deleted_at is not None

    # Not in active retrieval, not in default listing.
    assert mem.id not in {m.id for m in repo.retrieve_active("t1", "u1")}
    assert mem.id not in {m.id for m in repo.list_memories("t1", "u1")}
    # Still visible with include_deleted (for audit/forensics).
    assert mem.id in {m.id for m in repo.list_memories("t1", "u1", include_deleted=True)}


def test_delete_is_tenant_scoped(gateway, repo):
    _chat(gateway, "Remember that I prefer dark mode.")
    mem = repo.list_memories("t1", "u1")[0]
    # Wrong scope cannot delete.
    assert repo.soft_delete("t1", "other", mem.id) is None
    assert repo.get_memory("t1", "u1", mem.id).status == Status.active
