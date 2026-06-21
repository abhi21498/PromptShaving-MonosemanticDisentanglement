"""Parse + schema-validate provider text into trusted structured objects.

Providers return free text that may wrap JSON in markdown fences or prose. This
module extracts the JSON payload and validates it against a Pydantic model.
Any failure raises ``StructuredOutputError`` so the caller can fall back to the
deterministic heuristic instead of trusting malformed model output (ADR-008).
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# Strips a leading ```json / ``` fence and trailing fence if present.
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class StructuredOutputError(ValueError):
    """Raised when provider text is not valid JSON for the expected schema."""


def _extract_json_blob(text: str) -> str:
    """Best-effort isolation of the JSON object/array inside ``text``.

    Handles bare JSON, fenced code blocks, and JSON embedded in surrounding
    prose by slicing from the first opening brace/bracket to its matching close.
    """
    stripped = _FENCE.sub("", text.strip())
    stripped = stripped.strip()
    if not stripped:
        raise StructuredOutputError("empty provider output")
    if stripped[0] in "{[":
        return stripped
    # Embedded JSON: take the widest brace/bracket span.
    start = min(
        (i for i in (stripped.find("{"), stripped.find("[")) if i != -1),
        default=-1,
    )
    if start == -1:
        raise StructuredOutputError("no JSON object found in provider output")
    end = max(stripped.rfind("}"), stripped.rfind("]"))
    if end <= start:
        raise StructuredOutputError("unterminated JSON in provider output")
    return stripped[start : end + 1]


def parse_structured(text: str, model: type[T]) -> T:
    """Parse ``text`` into ``model``; raise ``StructuredOutputError`` on any issue."""
    blob = _extract_json_blob(text)
    try:
        data = json.loads(blob)
    except (json.JSONDecodeError, TypeError) as exc:
        raise StructuredOutputError(f"invalid JSON: {exc}") from exc
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise StructuredOutputError(f"schema validation failed: {exc}") from exc
