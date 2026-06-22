"""MemoryOps AI — Public Results Dashboard + Evidence Explorer (v0.9).

A READ-ONLY public evidence/demo surface. It explains MemoryOps and shows what
the system proves: the memory lifecycle, deletion compaction + vector purge
verification, worker runtime results, audit evidence, and validation results.

This dashboard is demo/evidence UI ONLY:
  - It reads static JSON from ./data — no live database, no secrets, no auth.
  - It performs no writes and exposes no admin controls.
  - The Next.js app in apps/web remains the official product / governance UI.

Run:
    cd apps/results-dashboard
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from components import cards, charts, flowcharts, timelines

DATA_DIR = Path(__file__).parent / "data"


@st.cache_data
def load(name: str) -> dict:
    """Load a static demo JSON artifact from ./data (read-only)."""
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def demo_banner() -> None:
    st.caption(
        "📖 Read-only public evidence/demo dashboard · static demo data · "
        "no live DB · no secrets · not the production UI"
    )


# --------------------------------------------------------------------------- #
# Page 1 — Overview
# --------------------------------------------------------------------------- #
def page_overview() -> None:
    rel = load("releases.json")
    st.title("MemoryOps AI — governed memory infrastructure for AI assistants")
    st.markdown(
        "Typed capture, policy evaluation, hybrid retrieval, lifecycle workers, "
        "deletion compaction, vector purge verification, tenant isolation, and "
        "audit evidence."
    )
    demo_banner()
    st.divider()

    cards.metric_row([
        ("Current version", rel["current_version"]),
        ("Next milestone", rel["next_version"]),
        ("Releases shipped", sum(1 for r in rel["releases"]
                                 if r["status"] == "Released")),
    ])

    st.subheader("Core promise")
    st.info(rel["core_promise"])

    st.subheader("Why AI memory needs governance")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Most AI 'memory' demos**")
        st.code("chat message → vector database → retrieve later", language="text")
    with col2:
        st.markdown("**MemoryOps AI**")
        st.code(
            "Capture → Evaluate → Store → Retrieve → Rank →\n"
            "Compose → Update → Forget → Audit",
            language="text",
        )

    st.subheader("Architecture summary")
    flowcharts.architecture_flow()
    st.markdown(f"**Repository:** {rel['repo_url']}")


# --------------------------------------------------------------------------- #
# Page 2 — Version Timeline
# --------------------------------------------------------------------------- #
def page_timeline() -> None:
    rel = load("releases.json")
    st.title("Version Timeline")
    st.caption("Progress from v0.1 through the current milestone.")
    demo_banner()
    st.divider()
    timelines.version_timeline(rel["releases"])
    st.divider()
    st.subheader("Release detail")
    for release in rel["releases"]:
        cards.release_card(release)


# --------------------------------------------------------------------------- #
# Page 3 — Memory Lifecycle Flow
# --------------------------------------------------------------------------- #
def page_lifecycle() -> None:
    demo = load("memory_lifecycle_demo.json")
    st.title("Memory Lifecycle Flow")
    st.caption("Capture → Evaluate → Store → Retrieve → Rank → Compose → "
               "Update → Forget → Audit")
    demo_banner()
    st.divider()
    flowcharts.lifecycle_flow()

    st.subheader("What each stage does")
    for stage in demo["stages"]:
        st.markdown(f"**{stage['stage']}** — {stage['what']}")
        st.caption(f"Invariant: {stage['invariant']}")

    st.divider()
    st.subheader("Example: a write")
    w = demo["example_write"]
    st.markdown(f"> {w['input_message']}")
    st.dataframe(w["extracted_candidates"], use_container_width=True,
                 hide_index=True)
    cards.metric_row([
        ("Stored", w["stored_count"]),
        ("Dropped", w["dropped_count"]),
        ("Blocked", w["blocked_count"]),
    ])
    st.caption("Audit events: " + ", ".join(f"`{e}`" for e in w["audit_events"]))

    st.subheader("Example: a read")
    r = demo["example_read"]
    st.markdown(f"> {r['query']}")
    st.dataframe(r["retrieved"], use_container_width=True, hide_index=True)
    cards.metric_row([
        ("Excluded (deleted)", r["excluded_deleted"]),
        ("Composed context (chars)", r["composed_context_chars"]),
    ])
    st.caption("Audit events: " + ", ".join(f"`{e}`" for e in r["audit_events"]))


# --------------------------------------------------------------------------- #
# Page 4 — Deletion Proof Explorer
# --------------------------------------------------------------------------- #
def page_deletion() -> None:
    demo = load("deletion_compaction_demo.json")
    st.title("Deletion Proof Explorer")
    st.caption("v0.7 — deletion compaction + vector purge verification. The "
               "strongest evidence MemoryOps provides.")
    demo_banner()
    st.divider()

    flowcharts.deletion_flow()

    col1, col2 = st.columns(2)
    with col1:
        cards.kv_block("Before compaction", demo["before"])
    with col2:
        cards.kv_block("After compaction", demo["after"])

    st.subheader("What happened")
    cards.labelled_list(demo["labels"], key="phase", value="result",
                        detail="detail")

    st.divider()
    st.warning("Scope: " + demo["scope_note"])


# --------------------------------------------------------------------------- #
# Page 5 — Worker Runtime Dashboard
# --------------------------------------------------------------------------- #
def page_workers() -> None:
    data = load("worker_runs.json")
    st.title("Worker Runtime Dashboard")
    st.caption("v0.6 lifecycle workers + v0.8 operable runtime "
               "(leases, retries, dead-letter, run history).")
    demo_banner()
    st.divider()

    st.subheader("Lifecycle jobs")
    st.dataframe(data["jobs"], use_container_width=True, hide_index=True)

    st.subheader("Per-job results (last run)")
    charts.job_results_bar(data["job_results"])
    st.dataframe(data["job_results"], use_container_width=True, hide_index=True)

    st.subheader("Audit events per job")
    charts.audit_count_chart(data["job_results"])

    st.subheader("Run history")
    charts.runs_table(data["runs"])
    st.caption("A `dead_letter` row is a run whose retries were exhausted — "
               "kept for inspection, never silently dropped.")

    st.subheader("Runtime features")
    for feat in data["runtime_features"]:
        st.markdown(f"- {feat}")


# --------------------------------------------------------------------------- #
# Page 6 — Audit Evidence Viewer
# --------------------------------------------------------------------------- #
def page_audit() -> None:
    data = load("audit_events.json")
    st.title("Audit Evidence Viewer")
    st.caption("MemoryOps doesn't just act — it records content-safe evidence "
               "of every lifecycle action.")
    demo_banner()
    st.divider()

    st.subheader("Deletion + compaction audit timeline")
    timelines.audit_timeline(data["deletion_compaction_timeline"])

    st.divider()
    st.subheader("Write-path audit timeline")
    timelines.audit_timeline(data["write_path_timeline"])

    st.divider()
    st.subheader("Event glossary")
    st.dataframe(data["event_glossary"], use_container_width=True,
                 hide_index=True)
    st.info(data["note"])


# --------------------------------------------------------------------------- #
# Page 7 — Validation Results
# --------------------------------------------------------------------------- #
def page_validation() -> None:
    data = load("validation.json")
    latest = data["latest"]
    st.title("Validation Results")
    st.caption("Build-quality evidence captured from local runs.")
    demo_banner()
    st.divider()

    cards.metric_row([
        ("pytest", latest["pytest"]),
        ("ruff", latest["ruff"]),
        ("evals", latest["evals"]),
    ])
    st.markdown(f"**PR invariant gate:** {latest['pr_invariant_gate']}")

    st.subheader("Loop evidence")
    st.dataframe(
        [{"loop": k, "result": v} for k, v in latest["loop_evidence"].items()],
        use_container_width=True, hide_index=True,
    )

    st.subheader("Version-by-version validation")
    st.dataframe(data["history"], use_container_width=True, hide_index=True)
    st.info(data["note"])


# --------------------------------------------------------------------------- #
# Page 8 — Roadmap + Honest Limitations
# --------------------------------------------------------------------------- #
def page_roadmap() -> None:
    data = load("roadmap.json")
    st.title("Roadmap + Honest Limitations")
    st.caption("Where MemoryOps is going — and what it deliberately does not "
               "claim.")
    demo_banner()
    st.divider()

    st.subheader("Forward roadmap")
    timelines.roadmap_timeline(data["milestones"])

    st.divider()
    st.subheader("Honest limitations")
    for lim in data["limitations"]:
        st.markdown(f"- {lim}")
    st.success("Stating limitations plainly is part of what makes the system "
               "trustworthy.")


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
PAGES = {
    "1 · Overview": page_overview,
    "2 · Version Timeline": page_timeline,
    "3 · Memory Lifecycle Flow": page_lifecycle,
    "4 · Deletion Proof Explorer": page_deletion,
    "5 · Worker Runtime Dashboard": page_workers,
    "6 · Audit Evidence Viewer": page_audit,
    "7 · Validation Results": page_validation,
    "8 · Roadmap + Limitations": page_roadmap,
}


def main() -> None:
    st.set_page_config(
        page_title="MemoryOps AI — Public Results Dashboard",
        page_icon="🧠",
        layout="wide",
    )
    st.sidebar.title("🧠 MemoryOps AI")
    st.sidebar.caption("Public Results Dashboard + Evidence Explorer (v0.9)")
    choice = st.sidebar.radio("Pages", list(PAGES.keys()), label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption(
        "Read-only · static demo data · no live DB · no secrets.\n\n"
        "The Next.js app (apps/web) remains the official product UI."
    )
    PAGES[choice]()


if __name__ == "__main__":
    main()
