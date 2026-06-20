"""Reliability primitives: timeouts, retry-with-backoff, and a circuit breaker.

These wrap fallible external calls (LLM, embeddings, DB reads) so a slow or
failing dependency degrades gracefully instead of cascading (invariant #4,
ADR-004). Inspired by production-readiness patterns: timeout every call, retry
transient faults, trip a breaker when a dependency is consistently unhealthy.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from tenacity import retry, stop_after_attempt, wait_exponential

T = TypeVar("T")


class CircuitBreakerOpen(Exception):
    """Raised when a breaker is open and the call is short-circuited."""


class CircuitBreaker:
    """Minimal circuit breaker.

    After ``threshold`` consecutive failures the breaker opens for
    ``reset_seconds``; calls during that window fail fast. One success closes it.
    """

    def __init__(self, name: str, threshold: int = 5, reset_seconds: float = 30.0) -> None:
        self.name = name
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.reset_seconds:
            # Half-open: allow a trial call.
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = time.monotonic()

    def call(self, fn: Callable[[], T]) -> T:
        if self.is_open:
            raise CircuitBreakerOpen(f"circuit '{self.name}' is open")
        try:
            result = fn()
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result


def with_retry(fn: Callable[[], T], attempts: int = 3) -> T:
    """Retry a callable with exponential backoff on any exception."""

    @retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.1, max=2.0),
        reraise=True,
    )
    def _runner() -> T:
        return fn()

    return _runner()


def safe_call(fn: Callable[[], T], default: T, *, label: str = "call") -> T:
    """Run ``fn`` and return ``default`` on any failure (graceful degradation).

    Used on the read path so retrieval failures never block a response.
    """
    try:
        return fn()
    except Exception:  # noqa: BLE001 — degradation boundary, deliberately broad
        from .logging import get_logger

        get_logger("memoryops.reliability").warning(
            "safe_call fell back to default", extra={"event": "degraded", "status": label}
        )
        return default
