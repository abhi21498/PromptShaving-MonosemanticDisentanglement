"""Lightweight chart renderers built on Streamlit's native charting + pandas."""

from __future__ import annotations

from typing import Sequence

import pandas as pd
import streamlit as st


def job_results_bar(job_results: Sequence[dict]) -> None:
    """Stacked bar of per-job scanned/changed/skipped/failed counts."""
    df = pd.DataFrame(job_results).set_index("job")
    cols = [c for c in ("scanned_count", "changed_count", "skipped_count",
                        "failed_count") if c in df.columns]
    pretty = df[cols].rename(columns=lambda c: c.replace("_count", "").title())
    st.bar_chart(pretty)


def runs_table(runs: Sequence[dict]) -> None:
    """Render worker run history as a dataframe."""
    df = pd.DataFrame(runs)
    keep = [c for c in ("id", "status", "attempts", "scanned_count",
                        "changed_count", "skipped_count", "error_count",
                        "started_at", "completed_at") if c in df.columns]
    st.dataframe(df[keep], use_container_width=True, hide_index=True)


def audit_count_chart(job_results: Sequence[dict]) -> None:
    """Bar of audit events emitted per job — evidence is recorded, not implied."""
    df = pd.DataFrame(job_results).set_index("job")[["audit_events"]]
    st.bar_chart(df.rename(columns={"audit_events": "Audit events"}))
