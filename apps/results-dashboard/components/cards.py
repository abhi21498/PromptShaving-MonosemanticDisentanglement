"""Card-style renderers: metrics, release cards, labelled key/value blocks."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

import streamlit as st

_STATUS_ICON = {
    "Released": "✅",
    "In progress": "🚧",
    "Planned": "⏳",
}


def metric_row(metrics: Sequence[tuple[str, object]]) -> None:
    """Render a horizontal row of st.metric tiles from (label, value) pairs."""
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)


def release_card(release: Mapping[str, object]) -> None:
    """Render a single release as an expandable card."""
    status = str(release.get("status", ""))
    icon = _STATUS_ICON.get(status, "•")
    version = release.get("version", "")
    title = release.get("title", "")
    with st.expander(f"{icon} {version} — {title}  ·  {status}"):
        st.write(release.get("summary", ""))
        for item in release.get("highlights", []) or []:
            st.markdown(f"- {item}")


def kv_block(title: str, data: Mapping[str, object]) -> None:
    """Render a titled block of key/value rows (used for before/after states)."""
    st.markdown(f"**{title}**")
    rows = "\n".join(
        f"| `{key}` | `{_fmt(value)}` |" for key, value in data.items()
    )
    st.markdown("| field | value |\n| --- | --- |\n" + rows)


def labelled_list(items: Iterable[Mapping[str, str]], *, key: str, value: str,
                  detail: str | None = None) -> None:
    """Render labelled rows like 'Phase — result' with optional detail text."""
    for item in items:
        line = f"**{item.get(key, '')}** — {item.get(value, '')}"
        st.markdown(line)
        if detail and item.get(detail):
            st.caption(item[detail])


def _fmt(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
