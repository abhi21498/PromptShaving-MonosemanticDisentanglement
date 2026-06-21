"""Vector candidate retrieval contract (v0.3).

Exercises ``Repository.search_candidates`` — the method both backends implement
identically (real pgvector on Postgres, cosine in-memory). These tests run on the
in-memory backend so they need no infra; the Postgres path is verified separately
in test_rls.py when a database is available.
"""

from __future__ import annotations

from app.db.entities import StoredMemory
from app.embeddings import embed
from app.schemas.memory import MemoryType, Sensitivity, Source, Status


def _mem(repo, tenant, user, content, status=Status.active):
    m = StoredMemory(
        tenant_id=tenant,
        user_id=user,
        memory_type=MemoryType.preference,
        content=content,
        importance=6,
        confidence=0.8,
        sensitivity=Sensitivity.low,
        status=status,
        source=Source(kind="manual", excerpt=content),
        embedding=embed(content),
    )
    return repo.create_memory(m)


def test_pgvector_returns_relevant_memory(repo):
    target = _mem(repo, "t1", "u1", "I prefer dark mode dashboards")
    _mem(repo, "t1", "u1", "the capital of France is Paris")
    pairs = repo.search_candidates("t1", "u1", embed("dark mode dashboards"))
    assert pairs, "expected at least one candidate"
    top_memory, top_sim = pairs[0]
    assert top_memory.id == target.id
    assert top_sim > 0.0


def test_wrong_tenant_not_returned(repo):
    _mem(repo, "t1", "u1", "I prefer dark mode dashboards")
    pairs = repo.search_candidates("t2", "u1", embed("dark mode dashboards"))
    assert pairs == []


def test_wrong_user_not_returned(repo):
    _mem(repo, "t1", "u1", "I prefer dark mode dashboards")
    pairs = repo.search_candidates("t1", "u2", embed("dark mode dashboards"))
    assert pairs == []


def test_deleted_memory_not_returned(repo):
    m = _mem(repo, "t1", "u1", "I prefer dark mode dashboards")
    repo.soft_delete("t1", "u1", m.id)
    pairs = repo.search_candidates("t1", "u1", embed("dark mode dashboards"))
    assert all(mem.id != m.id for mem, _ in pairs)


def test_empty_query_embedding_returns_active_rows_at_zero(repo):
    _mem(repo, "t1", "u1", "I prefer dark mode dashboards")
    pairs = repo.search_candidates("t1", "u1", [])
    assert pairs
    assert all(sim == 0.0 for _, sim in pairs)
