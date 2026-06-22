# Public Results Dashboard + Evidence Explorer (v0.9)

> **This is a public evidence/demo dashboard — not production UI.**
> The Next.js app in [`apps/web`](../apps/web) remains the official product /
> governance UI. The results dashboard reads static demo JSON; it never
> connects to production secrets, a live database, or real user data.

## Why this exists

After v0.8 MemoryOps had a deep backend: governed capture, policy evaluation,
hybrid retrieval, provider LLM adapters, a governance UI, background lifecycle
workers, deletion compaction, vector purge verification, audit evidence, and a
Railway-oriented worker runtime.

The remaining gap was **visibility**, not capability:

> People could not quickly see what MemoryOps does or what it proves.

v0.9 closes that gap with a read-only Streamlit "results viewer" that explains
the system and surfaces its evidence. It is deliberately **not** the product —
it is the public window onto what the product proves.

```text
Streamlit  = public evidence/demo layer  (this dashboard)
Next.js    = official product/admin governance UI  (apps/web)
FastAPI    = real backend                 (services/api)
Workers    = operational lifecycle system (services/worker)
```

## Where it lives

[`apps/results-dashboard/`](../apps/results-dashboard) — isolated from the core
API and the production path.

```text
apps/results-dashboard/
  app.py                     # 8-page Streamlit router
  requirements.txt           # streamlit + pandas
  README.md
  data/                      # static demo JSON artifacts (no real data)
    releases.json
    validation.json
    memory_lifecycle_demo.json
    deletion_compaction_demo.json
    worker_runs.json
    audit_events.json
    roadmap.json
  components/                # presentation-only helpers
    cards.py
    charts.py
    flowcharts.py
    timelines.py
```

## Pages

1. **Overview** — what MemoryOps is, why memory needs governance, architecture.
2. **Version Timeline** — v0.1 → v0.8 shipped, v0.9 in progress.
3. **Memory Lifecycle Flow** — Capture → Evaluate → Store → Retrieve → Rank →
   Compose → Update → Forget → Audit, with worked write/read examples.
4. **Deletion Proof Explorer** — before/after deletion compaction, vector purge
   verification, tombstone preservation (the strongest evidence MemoryOps has).
5. **Worker Runtime Dashboard** — per-job results and run history including a
   dead-lettered run.
6. **Audit Evidence Viewer** — content-safe audit-event timelines.
7. **Validation Results** — pytest / ruff / eval / PR-invariant-gate evidence.
8. **Roadmap + Honest Limitations** — what's next and what the system does not
   claim.

## Data and safety model

The dashboard renders only static JSON from `data/`. The shapes mirror the real
backend so the evidence is faithful:

- `worker_runs.json` follows the `worker_runs` table from
  [`infra/db/migrations/006_worker_runtime.sql`](../infra/db/migrations/006_worker_runtime.sql)
  (ids/counts/status only — never memory content).
- `audit_events.json` uses real `AuditService` event names
  (`memory_deleted`, `deletion_verification_passed`, `memory_content_compacted`,
  `memory_vector_purge_verified`, `memory_purge_tombstone_preserved`, …).

But every value is demo data. The dashboard has **no writes, no admin controls,
no auth, no live DB, and no secrets**, so it adds no risk to the production path.

## Honest limitations (shown in-app, page 8)

- Deletion compaction is **not** crypto-shred.
- No physical disk/page erasure guarantee.
- No full pgvector VACUUM/reindex orchestration yet.
- No cross-tenant scheduler until later.
- This Streamlit dashboard is **demo-only** and read-only.
- The Next.js app remains the official product UI.

## Running

```bash
cd apps/results-dashboard
pip install -r requirements.txt
streamlit run app.py
```

No environment variables or infrastructure are required. See
[`apps/results-dashboard/README.md`](../apps/results-dashboard/README.md).

## Relationship to the rest of the project

- This dashboard is **not** part of the chat request path, the policy broker, or
  any lifecycle invariant. It is an evidence surface, like the Hermes operator
  skills and phase gates — it makes the project easier to inspect and share.
- It does not replace, and must not be confused with, the Next.js governance UI.
- Deployment stays **Railway-only**; this dashboard is a local/optional viewer
  and introduces no Vercel dependency.
