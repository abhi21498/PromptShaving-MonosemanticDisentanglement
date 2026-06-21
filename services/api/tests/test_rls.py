"""Database-level Row-Level Security tests (v0.3, ADR-006).

These prove tenant isolation at the *database* layer (invariant #1, defense in
depth). They require a real Postgres with pgvector and therefore SKIP cleanly
when no database is reachable — so ``pytest -q`` stays infra-free and green.

Run against a database with, e.g.:
    DATABASE_URL=postgresql+psycopg://memoryops:memoryops@localhost:5432/memoryops \\
        pytest services/api/tests/test_rls.py
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
pytest.importorskip("pgvector")

from sqlalchemy import create_engine, text  # noqa: E402

_MIGRATIONS = Path(__file__).resolve().parents[3] / "infra" / "db" / "migrations"


def _database_url() -> str:
    return os.getenv("DATABASE_URL") or (
        "postgresql+psycopg://memoryops:memoryops@localhost:5432/memoryops"
    )


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(_database_url(), future=True)
    try:
        conn = eng.connect()
    except Exception as exc:  # noqa: BLE001 — no DB in this environment
        pytest.skip(f"Postgres not reachable: {type(exc).__name__}")
    conn.close()
    return eng


@pytest.fixture
def seeded(engine):
    """Apply migrations and seed two tenants, each with one memory row."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    with engine.begin() as conn:
        for name in ("001_extensions.sql", "002_core_tables.sql",
                     "003_indexes_rls.sql", "004_rls_policies.sql"):
            conn.execute(text((_MIGRATIONS / name).read_text()))
    # Inserts must run with a tenant context that satisfies the WITH CHECK policy.
    with engine.begin() as conn:
        for tid, uid, slug in ((tenant_a, user_a, "a"), (tenant_b, user_b, "b")):
            conn.execute(text("select set_config('app.tenant_id', :t, true)"), {"t": str(tid)})
            conn.execute(
                text("insert into tenants (id, slug, name) values (:id, :slug, :name)"),
                {"id": str(tid), "slug": f"rls-{slug}-{tid}", "name": f"RLS {slug}"},
            )
            conn.execute(
                text("insert into users (id, tenant_id, email) values (:id, :t, :e)"),
                {"id": str(uid), "t": str(tid), "e": f"{slug}@example.com"},
            )
            conn.execute(
                text(
                    "insert into memory_records (tenant_id, user_id, memory_type, content, source) "
                    "values (:t, :u, 'preference', :c, '{}'::jsonb)"
                ),
                {"t": str(tid), "u": str(uid), "c": f"secret for tenant {slug}"},
            )
    yield tenant_a, tenant_b
    with engine.begin() as conn:
        for tid in (tenant_a, tenant_b):
            conn.execute(text("select set_config('app.tenant_id', :t, true)"), {"t": str(tid)})
            conn.execute(text("delete from memory_records where tenant_id = :t"), {"t": str(tid)})
            conn.execute(text("delete from users where tenant_id = :t"), {"t": str(tid)})
            conn.execute(text("delete from tenants where id = :t"), {"t": str(tid)})


def test_rls_blocks_cross_tenant_query(engine, seeded):
    tenant_a, tenant_b = seeded
    with engine.begin() as conn:
        conn.execute(text("select set_config('app.tenant_id', :t, true)"), {"t": str(tenant_a)})
        rows = conn.execute(text("select tenant_id::text from memory_records")).scalars().all()
    assert rows, "tenant A should see its own row"
    assert all(r == str(tenant_a) for r in rows)
    assert str(tenant_b) not in rows


def test_rls_scopes_each_tenant(engine, seeded):
    tenant_a, tenant_b = seeded
    with engine.begin() as conn:
        conn.execute(text("select set_config('app.tenant_id', :t, true)"), {"t": str(tenant_b)})
        count_b = conn.execute(text("select count(*) from memory_records")).scalar_one()
    assert count_b == 1


def test_rls_enabled_and_forced(engine, seeded):
    with engine.begin() as conn:
        enabled, forced = conn.execute(
            text(
                "select relrowsecurity, relforcerowsecurity from pg_class "
                "where relname = 'memory_records'"
            )
        ).one()
    assert enabled and forced
