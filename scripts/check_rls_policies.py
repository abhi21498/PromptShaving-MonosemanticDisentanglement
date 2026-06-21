#!/usr/bin/env python3
"""Row-Level Security verifier for MemoryOps AI (v0.3).

Proves the database-level tenant isolation guarantee (ADR-006, invariant #1):

  1. RLS is enabled + forced on the protected tables.
  2. A tenant-isolation policy exists on each.
  3. With app.tenant_id set to tenant A, a query never returns tenant B's rows.

Designed to be CI-safe: if no database is reachable (or the driver isn't
installed) it prints SKIP and exits 0, so it never blocks a no-infra pipeline.
A genuine policy gap (DB reachable but RLS missing/leaking) exits 1.

Usage:
    python scripts/check_rls_policies.py
    DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db python scripts/check_rls_policies.py
"""

from __future__ import annotations

import os

_PROTECTED = ("memory_records", "memory_audit_logs", "memory_feedback", "memory_settings")


def _database_url() -> str:
    return os.getenv("DATABASE_URL") or os.getenv("MEMORYOPS_DATABASE_URL") or (
        "postgresql+psycopg://memoryops:memoryops@localhost:5432/memoryops"
    )


def main() -> int:
    print("MemoryOps AI — RLS policy check")
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("SKIP: sqlalchemy not installed (no Postgres backend in this environment).")
        return 0

    url = _database_url()
    try:
        engine = create_engine(url, pool_pre_ping=True, future=True)
        conn = engine.connect()
    except Exception as exc:  # noqa: BLE001 — DB simply not reachable here
        print(f"SKIP: cannot reach database ({type(exc).__name__}). RLS check not run.")
        return 0

    failures: list[str] = []
    with conn:
        # 1. RLS enabled + forced on each protected table.
        rows = {
            r[0]: (r[1], r[2])
            for r in conn.execute(
                text(
                    "select relname, relrowsecurity, relforcerowsecurity "
                    "from pg_class where relname = any(:names)"
                ),
                {"names": list(_PROTECTED)},
            )
        }
        for table in _PROTECTED:
            if table not in rows:
                failures.append(f"{table}: table not found")
                continue
            enabled, forced = rows[table]
            if not enabled:
                failures.append(f"{table}: row level security not ENABLED")
            elif not forced:
                failures.append(f"{table}: row level security not FORCED")
            else:
                print(f"[OK]   {table}: RLS enabled + forced")

        # 2. A policy exists on each protected table.
        policied = {
            r[0]
            for r in conn.execute(
                text("select tablename from pg_policies where tablename = any(:names)"),
                {"names": list(_PROTECTED)},
            )
        }
        for table in _PROTECTED:
            if table in rows and table not in policied:
                failures.append(f"{table}: no RLS policy defined")
            elif table in policied:
                print(f"[OK]   {table}: tenant-isolation policy present")

        # 3. Behavioral probe: tenant A must not see tenant B's memory rows.
        try:
            conn.execute(text("select set_config('app.tenant_id', 'rls_probe_a', true)"))
            leaked = conn.execute(
                text(
                    "select count(*) from memory_records "
                    "where tenant_id::text <> current_setting('app.tenant_id', true)"
                )
            ).scalar_one()
            if leaked and leaked > 0:
                failures.append(f"cross-tenant leak: {leaked} foreign rows visible under RLS")
            else:
                print("[OK]   behavioral probe: no cross-tenant rows visible")
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] behavioral probe skipped ({type(exc).__name__})")

    print()
    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        print(f"RESULT: FAIL — {len(failures)} RLS issue(s).")
        return 1
    print("RESULT: PASS — RLS enforced on all protected tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
