"""Graphviz DOT flowcharts. DOT strings render via st.graphviz_chart without
requiring the python graphviz package."""

from __future__ import annotations

import streamlit as st

_NODE = 'node [shape=box style="rounded,filled" fillcolor="#eef2ff" ' \
        'fontname="Helvetica" color="#6366f1"];'


def lifecycle_flow() -> None:
    """Capture -> Evaluate -> ... -> Audit, the core memory lifecycle."""
    stages = ["Capture", "Evaluate", "Store", "Retrieve", "Rank",
              "Compose", "Update", "Forget", "Audit"]
    edges = " -> ".join(f'"{s}"' for s in stages)
    st.graphviz_chart(
        f'digraph {{ rankdir=LR; {_NODE} {edges}; }}',
        use_container_width=True,
    )


def architecture_flow() -> None:
    """Backend -> evidence sources -> public dashboard -> audiences."""
    dot = f"""
    digraph {{
        rankdir=LR; {_NODE}
        "MemoryOps Backend" -> "Validation Artifacts";
        "MemoryOps Backend" -> "Worker Run Reports";
        "MemoryOps Backend" -> "Audit Events";
        "MemoryOps Backend" -> "Demo Memory Fixtures";
        "Validation Artifacts" -> "Public Results Dashboard";
        "Worker Run Reports" -> "Public Results Dashboard";
        "Audit Events" -> "Public Results Dashboard";
        "Demo Memory Fixtures" -> "Public Results Dashboard";
        "Public Results Dashboard" -> "Visitors / Recruiters / Builders";
    }}
    """
    st.graphviz_chart(dot, use_container_width=True)


def deletion_flow() -> None:
    """Soft delete -> verify -> compact -> purge-verify -> tombstone preserved."""
    dot = f"""
    digraph {{
        rankdir=LR; {_NODE}
        "Soft delete\\n(status=deleted)" -> "Deletion\\nverification";
        "Deletion\\nverification" -> "Retention\\nwindow elapses";
        "Retention\\nwindow elapses" -> "Content +\\nvector compaction";
        "Content +\\nvector compaction" -> "Vector purge\\nverification";
        "Vector purge\\nverification" -> "Tombstone\\npreserved";
    }}
    """
    st.graphviz_chart(dot, use_container_width=True)
