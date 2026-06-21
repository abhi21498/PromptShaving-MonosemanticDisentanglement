"""Provider-neutral LLM interface (v0.4).

The structured-memory-intelligence layer (extraction, evaluation, conflict
detection) talks to one synchronous ``LLMProvider`` protocol. A deterministic
``StubProvider`` is the default and the universal fallback target, so the system
stays fully functional with **no API keys** and tests never touch the network
(invariant #4, graceful degradation).

Synchronous on purpose: the MemoryOps write/read paths are sync end-to-end
(consistent with the embedding provider in ADR-006 and the compressor in
ADR-007). Network I/O and timeouts live inside each provider's ``complete``.

Providers return raw text. Turning that text into a validated structured object
is the job of ``structured_output`` — providers never decide policy, and an LLM
suggestion can never override the deterministic policy broker (ADR-003, ADR-008).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

# Known task names. ``task`` lets the deterministic StubProvider return the right
# shape of JSON without parsing the prompt; real providers send system+user to
# their API and ignore the distinction.
TASK_GENERAL = "general"
TASK_MEMORY_EXTRACTION = "memory_extraction"
TASK_MEMORY_EVALUATION = "memory_evaluation"
TASK_CONFLICT_DETECTION = "conflict_detection"
TASK_MERGE_RECOMMENDATION = "merge_recommendation"


class LLMError(Exception):
    """Base class for provider-layer failures (orchestrators fall back on these)."""


class LLMUnavailableError(LLMError):
    """Provider is unconfigured, missing a key, or its SDK is not installed."""


class LLMTimeoutError(LLMError):
    """Provider call exceeded the configured timeout."""


@runtime_checkable
class LLMProvider(Protocol):
    """Produces a text completion for a system+user prompt.

    ``task`` identifies the structured-intelligence operation so deterministic
    providers can respond appropriately; networked providers may ignore it.
    Implementations should raise an ``LLMError`` subclass on failure rather than
    returning junk, so the caller can fall back deterministically.
    """

    name: str

    def complete(self, *, system: str, user: str, task: str = TASK_GENERAL) -> str: ...
