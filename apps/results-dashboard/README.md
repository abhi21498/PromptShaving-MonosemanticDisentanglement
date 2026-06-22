# MemoryOps AI — Public Results Dashboard + Evidence Explorer (v0.9)

A **read-only public evidence/demo dashboard** built with Streamlit. It makes
MemoryOps AI understandable and inspectable at a glance — for GitHub, Hacker
News, Reddit, LinkedIn, recruiter, founder, and AI-infra audiences.

> This is **demo/evidence UI only**. It is **not** the production UI.
> The Next.js app in [`apps/web`](../web) remains the official product /
> governance UI. This dashboard reads static JSON from [`data/`](data) — it has
> **no live database, no secrets, no auth, and no write actions.**

## What it shows

| Page | Answers |
|------|---------|
| 1 · Overview | What is MemoryOps? Why does AI memory need governance? |
| 2 · Version Timeline | What shipped in v0.1 → v0.8, and what's next |
| 3 · Memory Lifecycle Flow | Capture → Evaluate → Store → Retrieve → Rank → Compose → Update → Forget → Audit |
| 4 · Deletion Proof Explorer | Before/after deletion compaction, vector purge verification, tombstone preservation |
| 5 · Worker Runtime Dashboard | Lifecycle job results + run history (leases, retries, dead-letter) |
| 6 · Audit Evidence Viewer | The audit-event timeline that proves actions are recorded |
| 7 · Validation Results | pytest / ruff / eval / PR-invariant-gate results |
| 8 · Roadmap + Honest Limitations | What's next, and what the system deliberately does not claim |

## Run it

```bash
cd apps/results-dashboard
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (default http://localhost:8501). No
environment variables, database, or API keys are required.

## How it's wired

```text
data/*.json  ──>  components/*.py  ──>  app.py (8 Streamlit pages)
```

- [`data/`](data) — static demo artifacts (releases, validation, lifecycle,
  deletion compaction, worker runs, audit events, roadmap). Shapes mirror the
  real backend (e.g. `worker_runs` from migration 006, real `AuditService`
  event names) but contain **only demo data** — no real user content.
- [`components/`](components) — presentation-only helpers (`cards`, `charts`,
  `flowcharts`, `timelines`). They never touch the core API.
- [`app.py`](app.py) — the page router.

## Guardrails (by design)

- Read-only. No writes, no admin controls, no auth.
- No connection to production secrets or real user data.
- No live DB required; everything renders from `data/*.json`.
- Isolated from the core API — adds no risk to the production path.

To refresh the demo numbers, edit the JSON files in [`data/`](data). Streamlit
caches them with `@st.cache_data`; use the app's "Rerun" / "Clear cache" menu to
pick up edits.

See [`docs/results-dashboard.md`](../../docs/results-dashboard.md) for the
project-level explanation of why this exists and how it fits the architecture.
