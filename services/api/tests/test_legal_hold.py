"""Legal hold is a fail-closed override across the lifecycle (v0.10, ADR-013).

A memory on legal hold must survive every forgetting path: decay leaves it
untouched, archive never archives it, and deletion compaction never clears a
held (even already-deleted) memory's content — preserving it for discovery while
keeping the override auditable.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.db import governance as gov
from app.schemas.memory import Status
from app.workers.archive import ArchiveWorker
from app.workers.decay import DecayWorker
from app.workers.deletion_compaction import DeletionCompactionWorker
from app.workers.lifecycle import WorkerContext
from app.workers.schemas import MEMORY_LEGAL_HOLD_COMPACTION_BLOCKED

from ._worker_helpers import seed_memory

NOW = datetime(2026, 6, 21, tzinfo=UTC)


def _ctx(**kw) -> WorkerContext:
    kw.setdefault("tenant_id", "t1")
    kw.setdefault("user_id", "u1")
    kw.setdefault("now", NOW)
    return WorkerContext(**kw)


def _hold(repo, mem):
    gov.set_legal_hold(mem, on=True, reason="litigation", now=NOW)
    return repo.update_memory(mem)


def test_decay_skips_legal_hold(repo) -> None:
    mem = seed_memory(repo, importance=8, confidence=0.1, age_days=400)
    _hold(repo, mem)
    DecayWorker(repo).run(_ctx())
    # Importance untouched: held memory is frozen.
    assert repo.get_memory("t1", "u1", mem.id).importance == 8


def test_archive_skips_legal_hold(repo) -> None:
    mem = seed_memory(repo, age_days=500)
    _hold(repo, mem)
    ArchiveWorker(repo).run(_ctx())
    assert repo.get_memory("t1", "u1", mem.id).status == Status.active


def test_compaction_preserves_held_deleted_memory(repo) -> None:
    mem = seed_memory(repo, content="held evidence", status=Status.deleted, age_days=500)
    mem.embedding = [0.1, 0.2, 0.3]
    _hold(repo, mem)
    result = DeletionCompactionWorker(repo).run(_ctx())

    row = repo.get_memory("t1", "u1", mem.id)
    # Content + vector material are PRESERVED under hold (not compacted).
    assert row.content == "held evidence"
    assert row.embedding == [0.1, 0.2, 0.3]
    assert result.details["legal_hold_blocked_count"] == 1
    assert result.details["compacted_count"] == 0
    actions = [e.action for e in repo.list_audit("t1", "u1")]
    assert MEMORY_LEGAL_HOLD_COMPACTION_BLOCKED in actions


def test_releasing_hold_allows_compaction(repo) -> None:
    mem = seed_memory(repo, content="releasable", status=Status.deleted, age_days=500)
    _hold(repo, mem)
    DeletionCompactionWorker(repo).run(_ctx())
    assert repo.get_memory("t1", "u1", mem.id).content == "releasable"  # blocked

    # Release the hold; now compaction proceeds.
    held = repo.get_memory("t1", "u1", mem.id)
    gov.set_legal_hold(held, on=False, now=NOW)
    repo.update_memory(held)
    DeletionCompactionWorker(repo).run(_ctx())
    assert repo.get_memory("t1", "u1", mem.id).content == ""
