"""Structured-output parsing: valid JSON parses, malformed raises cleanly."""

from __future__ import annotations

import pytest

from app.llm import MemoryExtractionResult
from app.llm.schemas import ConflictDetectionResult
from app.llm.structured_output import StructuredOutputError, parse_structured


def test_parses_plain_json() -> None:
    text = '{"memories": [{"content": "x", "type": "semantic"}]}'
    result = parse_structured(text, MemoryExtractionResult)
    assert len(result.memories) == 1


def test_parses_fenced_json() -> None:
    text = '```json\n{"memories": []}\n```'
    assert parse_structured(text, MemoryExtractionResult).memories == []


def test_parses_json_embedded_in_prose() -> None:
    text = 'Sure! Here is the result: {"has_conflict": false, "conflicts": []} Done.'
    assert parse_structured(text, ConflictDetectionResult).has_conflict is False


def test_invalid_json_raises_structured_error() -> None:
    with pytest.raises(StructuredOutputError):
        parse_structured("not json at all", MemoryExtractionResult)


def test_malformed_json_raises_structured_error() -> None:
    with pytest.raises(StructuredOutputError):
        parse_structured('{"memories": [unquoted]}', MemoryExtractionResult)


def test_schema_mismatch_raises_structured_error() -> None:
    # importance out of range fails schema validation.
    text = '{"memories": [{"content": "x", "importance": 99}]}'
    with pytest.raises(StructuredOutputError):
        parse_structured(text, MemoryExtractionResult)


def test_empty_output_raises_structured_error() -> None:
    with pytest.raises(StructuredOutputError):
        parse_structured("   ", MemoryExtractionResult)
