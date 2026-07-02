"""Memory Usage Trace + admission through the gateway (v1.3, ADR-017).

End-to-end read path: the trace explains why each memory was (or wasn't) allowed
into context, and consent withdrawal denies admission to still-active memory.
"""

from __future__ import annotations

from app.db import governance as gov
from app.schemas.memory import ChatRequest


def _chat(gateway, message, **kw):
    return gateway.handle_chat(
        ChatRequest(tenant_id="t1", user_id="u1", message=message, **kw), trace_id="tr"
    )


def test_trace_explains_admitted_memory(gateway):
    _chat(gateway, "Remember that I prefer Vendor X for cloud.")
    resp = _chat(gateway, "Which vendor do I prefer?")

    assert resp.trace is not None
    assert resp.trace.response_id == resp.trace_id
    assert resp.trace.memories_used, "expected the relevant memory to be admitted"
    entry = resp.trace.memories_used[0]
    assert entry.admission_decision == "ALLOW"
    assert entry.admission_reason
    assert entry.consent_status == "granted"
    assert entry.stored_at is not None
    assert entry.source.kind  # provenance is present (invariant #3)
    assert resp.trace.admission_counts.get("ALLOW", 0) >= 1


def test_consent_withdrawn_memory_denied_admission_and_audited(gateway, repo):
    _chat(gateway, "Remember that I prefer Vendor X for cloud.")
    mem = repo.list_memories("t1", "u1")[0]
    gov.set_consent(mem, status=gov.ConsentStatus.withdrawn)
    repo.update_memory(mem)

    resp = _chat(gateway, "Which vendor do I prefer?")

    # Not used to answer …
    assert all(u.memory_id != mem.id for u in resp.used_memories)
    # … and surfaced as blocked in the trace with a reason.
    blocked_ids = {e.memory_id for e in resp.trace.memories_blocked}
    assert mem.id in blocked_ids
    blocked = next(e for e in resp.trace.memories_blocked if e.memory_id == mem.id)
    assert blocked.admission_decision == "BLOCK_CONSENT_WITHDRAWN"

    # A content-free admission audit event was appended (invariant #7).
    actions = [e.action for e in repo.list_audit("t1", "u1", limit=200)]
    assert "context_admission_blocked" in actions


def test_trace_can_be_disabled(gateway, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("MEMORYOPS_MEMORY_TRACE", "false")
    get_settings.cache_clear()
    try:
        _chat(gateway, "Remember that I prefer Vendor X for cloud.")
        resp = _chat(gateway, "Which vendor do I prefer?")
        assert resp.trace is None
        # Disabling the trace does not disable retrieval.
        assert resp.used_memories
    finally:
        get_settings.cache_clear()
