"""Governance metadata helpers (v0.10, ADR-013).

Unit-tests app/db/governance.py: legal hold, pins, protection, consent
resolution, retention bookkeeping, and the content-free public summary.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.db import governance as gov

from ._worker_helpers import seed_memory

NOW = datetime(2026, 6, 21, tzinfo=UTC)


def test_legal_hold_round_trip(repo) -> None:
    mem = seed_memory(repo)
    assert not gov.is_legal_hold(mem)
    gov.set_legal_hold(mem, on=True, reason="subpoena", now=NOW)
    assert gov.is_legal_hold(mem)
    assert gov.legal_hold_reason(mem) == "subpoena"
    gov.set_legal_hold(mem, on=False, now=NOW)
    assert not gov.is_legal_hold(mem)
    assert gov.legal_hold_reason(mem) is None


def test_pin_and_protect_flags(repo) -> None:
    mem = seed_memory(repo)
    gov.set_pinned(mem, on=True)
    gov.set_protected(mem, on=True)
    assert gov.is_pinned(mem) and gov.is_protected(mem)
    assert gov.is_retention_exempt(mem)
    assert set(gov.retention_blockers(mem)) == {"pinned", "protected"}


def test_consent_defaults_to_granted(repo) -> None:
    mem = seed_memory(repo)
    assert gov.consent_status(mem, now=NOW) == gov.ConsentStatus.granted


def test_consent_expiry_resolves_to_expired(repo) -> None:
    mem = seed_memory(repo)
    past = datetime(2026, 1, 1, tzinfo=UTC)
    gov.set_consent(mem, status=gov.ConsentStatus.granted, expires_at=past, now=NOW)
    assert gov.consent_status(mem, now=NOW) == gov.ConsentStatus.expired


def test_withdrawn_consent_sticks(repo) -> None:
    mem = seed_memory(repo)
    gov.set_consent(mem, status=gov.ConsentStatus.withdrawn, now=NOW)
    assert gov.consent_status(mem, now=NOW) == gov.ConsentStatus.withdrawn


def test_set_retention_bookkeeping(repo) -> None:
    mem = seed_memory(repo)
    expires = datetime(2027, 6, 21, tzinfo=UTC)
    gov.set_retention(mem, policy="default", expires_at=expires, now=NOW)
    state = gov.retention_state(mem)
    assert state["policy"] == "default"
    assert state["expires_at"] == expires.isoformat()


def test_public_governance_is_content_free(repo) -> None:
    mem = seed_memory(repo, content="my home address is secret")
    gov.set_legal_hold(mem, on=True, reason="hold", now=NOW)
    summary = gov.public_governance(mem, now=NOW)
    assert "my home address" not in str(summary)
    assert summary["legal_hold"] is True
    assert summary["consent_status"] == gov.ConsentStatus.granted
