"""Retention policy engine (v0.10, ADR-013).

Unit-tests the deterministic retention evaluator: sensitivity → window mapping,
override precedence (hold/pin/protect win), consent-driven eligibility, and the
admin-readable decision shape. No DB, no API keys.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.db import governance as gov
from app.schemas.memory import Sensitivity
from app.services.retention import (
    DEFAULT_POLICY,
    STRICT_POLICY,
    RetentionOutcome,
    evaluate,
    get_policy,
)

from ._worker_helpers import seed_memory

NOW = datetime(2026, 6, 21, tzinfo=UTC)


def test_get_policy_falls_back_to_default() -> None:
    assert get_policy(None) is DEFAULT_POLICY
    assert get_policy("does-not-exist") is DEFAULT_POLICY
    assert get_policy("strict") is STRICT_POLICY


def test_high_sensitivity_expires_sooner_than_low(repo) -> None:
    # default: high=90d, low=365d. At 100 days, high is expired, low is retained.
    high = seed_memory(repo, content="ssn", sensitivity=Sensitivity.high, age_days=100)
    low = seed_memory(repo, content="likes tea", sensitivity=Sensitivity.low, age_days=100)
    assert evaluate(high, now=NOW).outcome is RetentionOutcome.expired
    assert evaluate(low, now=NOW).outcome is RetentionOutcome.retain


def test_strict_policy_shortens_windows(repo) -> None:
    mem = seed_memory(repo, sensitivity=Sensitivity.high, age_days=40)
    assert evaluate(mem, now=NOW, policy=DEFAULT_POLICY).outcome is RetentionOutcome.retain  # 90d
    assert evaluate(mem, now=NOW, policy=STRICT_POLICY).outcome is RetentionOutcome.expired  # 30d


def test_legal_hold_overrides_expired_window(repo) -> None:
    mem = seed_memory(repo, sensitivity=Sensitivity.high, age_days=500)
    gov.set_legal_hold(mem, on=True, reason="litigation", now=NOW)
    decision = evaluate(mem, now=NOW)
    assert decision.outcome is RetentionOutcome.held
    assert "legal_hold" in decision.blocked_by
    assert not decision.eligible_for_deletion


def test_pinned_and_protected_block_deletion(repo) -> None:
    pinned = seed_memory(repo, age_days=500, metadata={"pinned": True})
    protected = seed_memory(repo, age_days=500, metadata={"protected": True})
    assert evaluate(pinned, now=NOW).outcome is RetentionOutcome.held
    assert evaluate(protected, now=NOW).blocked_by == ["protected"]


def test_withdrawn_consent_is_eligible_regardless_of_age(repo) -> None:
    mem = seed_memory(repo, age_days=1)  # young, would otherwise be retained
    gov.set_consent(mem, status=gov.ConsentStatus.withdrawn, now=NOW)
    decision = evaluate(mem, now=NOW)
    assert decision.outcome is RetentionOutcome.consent_revoked
    assert decision.eligible_for_deletion


def test_expired_consent_window_makes_memory_eligible(repo) -> None:
    mem = seed_memory(repo, age_days=1)
    past = datetime(2026, 1, 1, tzinfo=UTC)
    gov.set_consent(mem, status=gov.ConsentStatus.granted, expires_at=past, now=NOW)
    assert evaluate(mem, now=NOW).outcome is RetentionOutcome.consent_revoked


def test_missing_consent_defaults_to_granted(repo) -> None:
    mem = seed_memory(repo, age_days=1)
    assert evaluate(mem, now=NOW).consent_status == gov.ConsentStatus.granted


def test_decision_dict_is_content_free(repo) -> None:
    mem = seed_memory(repo, content="super secret content", age_days=500)
    payload = evaluate(mem, now=NOW).to_dict()
    assert "super secret content" not in str(payload)
    assert payload["memory_id"] == mem.id
    assert set(payload) >= {"outcome", "policy", "blocked_by", "eligible_for_deletion"}
