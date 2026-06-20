"""Tenant isolation (invariant #1): no cross-tenant / cross-user retrieval."""

from __future__ import annotations

from app.schemas.memory import ChatRequest


def _chat(gateway, tenant, user, message):
    return gateway.handle_chat(
        ChatRequest(tenant_id=tenant, user_id=user, message=message), trace_id="test"
    )


def test_other_tenant_memory_not_retrieved(gateway, repo):
    _chat(gateway, "tenant_acme", "user_acme", "Remember Acme's roadmap is confidential.")
    # A different tenant must see nothing.
    assert repo.retrieve_active("tenant_demo", "user_demo") == []
    assert repo.list_memories("tenant_demo", "user_demo") == []


def test_other_user_same_tenant_not_retrieved(gateway, repo):
    _chat(gateway, "t1", "alice", "Remember Alice prefers tabs over spaces.")
    assert repo.retrieve_active("t1", "bob") == []


def test_get_memory_is_tenant_scoped(gateway, repo):
    _chat(gateway, "t1", "alice", "Remember Alice likes dark mode.")
    mem_id = repo.list_memories("t1", "alice")[0].id
    # Right scope returns it; wrong scope does not.
    assert repo.get_memory("t1", "alice", mem_id) is not None
    assert repo.get_memory("t1", "bob", mem_id) is None
    assert repo.get_memory("t2", "alice", mem_id) is None
