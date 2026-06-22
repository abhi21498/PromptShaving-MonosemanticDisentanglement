"""Vertical timeline renderers for releases and audit-event sequences."""

from __future__ import annotations

from typing import Sequence

import streamlit as st

_STATUS_ICON = {"Released": "✅", "In progress": "🚧", "Planned": "⏳"}


def version_timeline(releases: Sequence[dict]) -> None:
    """Render a vertical version timeline from release records."""
    for rel in releases:
        icon = _STATUS_ICON.get(str(rel.get("status", "")), "•")
        st.markdown(
            f"{icon} **{rel.get('version','')}** — {rel.get('title','')}  "
            f"<span style='color:#888'>· {rel.get('status','')}</span>",
            unsafe_allow_html=True,
        )
        if rel.get("summary"):
            st.caption(rel["summary"])


def audit_timeline(events: Sequence[dict]) -> None:
    """Render an ordered audit-event sequence with detail captions."""
    for ev in events:
        seq = ev.get("seq")
        prefix = f"`{seq}` " if seq is not None else ""
        st.markdown(f"{prefix}**`{ev.get('event','')}`**")
        if ev.get("detail"):
            st.caption(ev["detail"])


def roadmap_timeline(milestones: Sequence[dict]) -> None:
    """Render forward roadmap milestones with goals."""
    for m in milestones:
        icon = _STATUS_ICON.get(str(m.get("status", "")), "•")
        st.markdown(
            f"{icon} **{m.get('version','')} — {m.get('title','')}**  "
            f"<span style='color:#888'>· {m.get('status','')}</span>",
            unsafe_allow_html=True,
        )
        if m.get("goal"):
            st.caption(m["goal"])
