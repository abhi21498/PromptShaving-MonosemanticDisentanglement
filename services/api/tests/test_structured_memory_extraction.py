"""Structured extraction orchestration: stub path is structured + deterministic."""

from __future__ import annotations

from app.core.config import Settings
from app.llm import StubProvider, extract_memories
from app.schemas.memory import MemoryType, Source
from app.services.extractor import Extractor


def test_stub_extraction_is_structured_mode() -> None:
    outcome = extract_memories(StubProvider(), "Remember that I prefer concise answers.")
    assert outcome.mode == "structured"
    assert outcome.provider == "stub"
    assert len(outcome.memories) == 1
    assert outcome.memories[0].type == MemoryType.preference


def test_extractor_maps_to_candidate_with_provenance() -> None:
    ex = Extractor(provider=StubProvider())
    src = Source(kind="chat", excerpt="orig message")
    candidates = ex.extract("I'm building MemoryOps AI for a hackathon.", src)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.type == MemoryType.project
    assert cand.source.excerpt == "orig message"  # invariant #3: provenance preserved


def test_extractor_emits_no_candidate_for_question() -> None:
    ex = Extractor(provider=StubProvider())
    assert ex.extract("What editor should I use?", Source()) == []


def test_strict_mode_without_fallback_extracts_nothing_on_bad_provider() -> None:
    # A provider that always raises + fallback disabled → safe empty (never blocks).
    class _Broken:
        name = "broken"

        def complete(self, *, system: str, user: str, task: str = "general") -> str:
            raise RuntimeError("boom")

    settings = Settings(llm_fallback_to_heuristic=False)
    outcome = extract_memories(_Broken(), "Remember that I prefer dark mode.", settings=settings)
    assert outcome.mode == "strict_empty"
    assert outcome.memories == []
