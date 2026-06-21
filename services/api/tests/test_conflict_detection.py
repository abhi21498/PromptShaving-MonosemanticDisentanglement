"""Conflict detection: structured via stub, heuristic on fallback, advisory only."""

from __future__ import annotations

from app.core.config import Settings
from app.llm import StubProvider, detect_conflicts
from app.llm.base import LLMUnavailableError
from app.llm.fallback import heuristic_conflicts


def test_detects_contradiction_via_stub() -> None:
    outcome = detect_conflicts(
        StubProvider(),
        "I no longer prefer dark mode dashboards.",
        [("m1", "I prefer dark mode dashboards.")],
    )
    assert outcome.mode == "structured"
    assert outcome.result.has_conflict is True
    assert outcome.result.conflicts[0].existing_memory_id == "m1"


def test_no_conflict_when_unrelated() -> None:
    outcome = detect_conflicts(
        StubProvider(),
        "I prefer dark mode dashboards.",
        [("m1", "I am building a memory governance system.")],
    )
    assert outcome.result.has_conflict is False


def test_no_conflict_when_aligned() -> None:
    # Same polarity, overlapping subject → not a contradiction.
    outcome = detect_conflicts(
        StubProvider(),
        "I prefer dark mode dashboards.",
        [("m1", "I prefer dark mode dashboards everywhere.")],
    )
    assert outcome.result.has_conflict is False


def test_falls_back_to_heuristic_on_provider_failure() -> None:
    class _Broken:
        name = "broken"

        def complete(self, *, system: str, user: str, task: str = "general") -> str:
            raise LLMUnavailableError("boom")

    outcome = detect_conflicts(
        _Broken(),
        "I no longer prefer dark mode dashboards.",
        [("m1", "I prefer dark mode dashboards.")],
    )
    assert outcome.mode == "heuristic"
    assert outcome.result.has_conflict is True


def test_heuristic_conflicts_directly() -> None:
    result = heuristic_conflicts(
        "I never use VS Code anymore.", [("m1", "I always use VS Code as my editor.")]
    )
    assert result.has_conflict is True
    assert result.conflicts[0].relation == "contradicts"


def test_empty_existing_yields_no_conflict() -> None:
    outcome = detect_conflicts(StubProvider(), "I prefer dark mode.", [])
    assert outcome.result.has_conflict is False


def test_fallback_disabled_returns_empty_conflicts() -> None:
    class _Broken:
        name = "broken"

        def complete(self, *, system: str, user: str, task: str = "general") -> str:
            raise LLMUnavailableError("boom")

    outcome = detect_conflicts(
        _Broken(),
        "I no longer prefer dark mode dashboards.",
        [("m1", "I prefer dark mode dashboards.")],
        settings=Settings(llm_fallback_to_heuristic=False),
    )
    assert outcome.result.has_conflict is False
