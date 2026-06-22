"""Retention worker (v0.10, ADR-013).

Proves the retention layer: active memory past its window (or with revoked
consent) is soft-deleted under an enabled policy, legal-hold/pin/protected memory
is preserved, the worker is OFF by default (preview only), dry-run deletes
nothing, it is idempotent, tenant-scoped, and records admin-readable decisions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.db import governance as gov
from app.schemas.memory import Sensitivity, Status
from app.workers.lifecycle import WorkerContext
from app.workers.retention import RetentionWorker
from app.workers.schemas import (
    MEMORY_CONSENT_REVOKED,
    MEMORY_RETENTION_EXPIRED,
    MEMORY_RETENTION_HOLD_RESPECTED,
    RETENTION_DECISION_RECORDED,
)

from ._worker_helpers import seed_memory

NOW = datetime(2026, 6, 21, tzinfo=UTC)


def _ctx(**kw) -> WorkerContext:
    kw.setdefault("tenant_id", "t1")
    kw.setdefault("user_id", "u1")
    kw.setdefault("now", NOW)
    return WorkerContext(**kw)


def _actions(repo, tenant="t1", user="u1"):
    return [e.action for e in repo.list_audit(tenant, user)]


def _enabled(repo):
    return RetentionWorker(repo, enabled=True)


# ── core behavior ───────────────────────────────────────────────────────────────
def test_expired_memory_is_soft_deleted_when_enabled(repo) -> None:
    mem = seed_memory(repo, sensitivity=Sensitivity.high, age_days=200)  # default high=90d
    result = _enabled(repo).run(_ctx())

    assert result.details["expired_count"] == 1
    assert result.details["deleted_count"] == 1
    assert repo.get_memory("t1", "u1", mem.id).status == Status.deleted
    assert MEMORY_RETENTION_EXPIRED in _actions(repo)
    assert RETENTION_DECISION_RECORDED in _actions(repo)


def test_fresh_memory_is_retained(repo) -> None:
    mem = seed_memory(repo, age_days=1)
    _enabled(repo).run(_ctx())
    assert repo.get_memory("t1", "u1", mem.id).status == Status.active


def test_withdrawn_consent_triggers_deletion(repo) -> None:
    mem = seed_memory(repo, age_days=1)
    gov.set_consent(mem, status=gov.ConsentStatus.withdrawn, now=NOW)
    repo.update_memory(mem)
    result = _enabled(repo).run(_ctx())
    assert result.details["consent_revoked_count"] == 1
    assert repo.get_memory("t1", "u1", mem.id).status == Status.deleted
    assert MEMORY_CONSENT_REVOKED in _actions(repo)


# ── overrides ────────────────────────────────────────────────────────────────────
def test_legal_hold_memory_is_never_deleted(repo) -> None:
    mem = seed_memory(repo, sensitivity=Sensitivity.high, age_days=500)
    gov.set_legal_hold(mem, on=True, reason="litigation", now=NOW)
    repo.update_memory(mem)
    result = _enabled(repo).run(_ctx())
    assert result.details["held_count"] == 1
    assert result.details["deleted_count"] == 0
    assert repo.get_memory("t1", "u1", mem.id).status == Status.active
    assert MEMORY_RETENTION_HOLD_RESPECTED in _actions(repo)


def test_pinned_and_protected_memory_is_preserved(repo) -> None:
    pinned = seed_memory(repo, age_days=500, metadata={"pinned": True})
    protected = seed_memory(repo, age_days=500, metadata={"protected": True})
    _enabled(repo).run(_ctx())
    assert repo.get_memory("t1", "u1", pinned.id).status == Status.active
    assert repo.get_memory("t1", "u1", protected.id).status == Status.active


# ── safety / governance ─────────────────────────────────────────────────────────
def test_disabled_worker_previews_but_deletes_nothing(repo) -> None:
    mem = seed_memory(repo, sensitivity=Sensitivity.high, age_days=500)
    result = RetentionWorker(repo, enabled=False).run(_ctx())
    assert result.details["expired_count"] == 1  # decision still recorded
    assert result.details["deleted_count"] == 0
    assert repo.get_memory("t1", "u1", mem.id).status == Status.active
    assert RETENTION_DECISION_RECORDED in _actions(repo)


def test_dry_run_deletes_nothing(repo) -> None:
    mem = seed_memory(repo, sensitivity=Sensitivity.high, age_days=500)
    result = _enabled(repo).run(_ctx(dry_run=True))
    assert result.details["deleted_count"] == 0
    assert repo.get_memory("t1", "u1", mem.id).status == Status.active


def test_idempotent_second_run_is_a_noop(repo) -> None:
    seed_memory(repo, sensitivity=Sensitivity.high, age_days=500)
    _enabled(repo).run(_ctx())
    second = _enabled(repo).run(_ctx())
    # The deleted row left the active set, so the second pass scans/deletes nothing.
    assert second.details["scanned_count"] == 0
    assert second.details["deleted_count"] == 0


def test_deleted_memory_is_never_resurrected(repo) -> None:
    deleted = seed_memory(repo, status=Status.deleted, age_days=500)
    _enabled(repo).run(_ctx())
    assert repo.get_memory("t1", "u1", deleted.id).status == Status.deleted


def test_tenant_scoped_does_not_touch_other_tenant(repo) -> None:
    mine = seed_memory(repo, tenant_id="t1", sensitivity=Sensitivity.high, age_days=500)
    other = seed_memory(repo, tenant_id="t2", sensitivity=Sensitivity.high, age_days=500)
    _enabled(repo).run(_ctx(tenant_id="t1"))
    assert repo.get_memory("t1", "u1", mine.id).status == Status.deleted
    assert repo.get_memory("t2", "u1", other.id).status == Status.active
