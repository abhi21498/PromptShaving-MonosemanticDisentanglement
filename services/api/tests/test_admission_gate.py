"""Context Admission Gate — unit tests (v1.3, ADR-017).

Exercises the per-memory admission verdicts directly on the gate, independent of
the retriever/ranker, so the opt-in gates (sensitivity, low-confidence) and the
defense-in-depth blocks (wrong-tenant, deleted, archived) are covered without
having to route through the policy broker.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import get_settings
from app.db import governance as gov
from app.db.entities import StoredMemory
from app.schemas.memory import MemoryType, Sensitivity, Source, Status
from app.services.admission_gate import AdmissionDecision, AdmissionGate
from app.services.ranker import RankedMemory
from app.services.retriever import ScoredCandidate


def _mem(**kw) -> StoredMemory:
    defaults = dict(
        tenant_id="t1",
        user_id="u1",
        memory_type=MemoryType.semantic,
        content="user prefers vendor x",
        importance=5,
        confidence=0.8,
        sensitivity=Sensitivity.low,
        status=Status.active,
        source=Source(kind="chat"),
    )
    defaults.update(kw)
    return StoredMemory(**defaults)


def _ranked(memory: StoredMemory, score: float = 0.8) -> RankedMemory:
    cand = ScoredCandidate(memory=memory, semantic=score, keyword=0.5)
    return RankedMemory(candidate=cand, score=score, score_breakdown={"vector_similarity": score})


@pytest.fixture(autouse=True)
def _fresh_settings():
    # The gate reads the lru_cached settings; keep every test isolated from env.
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _evaluate(ranked, tenant_id="t1", user_id="u1"):
    return AdmissionGate().evaluate([ranked], tenant_id=tenant_id, user_id=user_id)


def test_active_consent_granted_is_allowed():
    result = _evaluate(_ranked(_mem()))
    (rec,) = result.records
    assert rec.decision is AdmissionDecision.ALLOW
    assert rec.consent_status == gov.ConsentStatus.granted
    assert result.admitted  # reaches the composer


def test_wrong_tenant_blocked():
    rec = _evaluate(_ranked(_mem(tenant_id="other"))).records[0]
    assert rec.decision is AdmissionDecision.BLOCK_WRONG_TENANT


def test_deleted_and_archived_blocked():
    assert _evaluate(_ranked(_mem(status=Status.deleted))).records[0].decision \
        is AdmissionDecision.BLOCK_DELETED
    assert _evaluate(_ranked(_mem(status=Status.archived))).records[0].decision \
        is AdmissionDecision.BLOCK_ARCHIVED


def test_consent_withdrawn_blocked():
    m = _mem()
    gov.set_consent(m, status=gov.ConsentStatus.withdrawn)
    rec = _evaluate(_ranked(m)).records[0]
    assert rec.decision is AdmissionDecision.BLOCK_CONSENT_WITHDRAWN


def test_retention_expired_blocked_but_legal_hold_is_exempt():
    past = datetime.now(UTC) - timedelta(days=1)
    m = _mem()
    gov.set_retention(m, policy="strict", expires_at=past)
    rec = _evaluate(_ranked(m)).records[0]
    assert rec.decision is AdmissionDecision.BLOCK_EXPIRED
    assert rec.retention_status == "expired"

    # Legal hold is a preservation control → retention-exempt, so it is allowed.
    gov.set_legal_hold(m, on=True, reason="litigation")
    rec2 = _evaluate(_ranked(m)).records[0]
    assert rec2.decision is AdmissionDecision.ALLOW
    assert rec2.retention_status == "exempt"


def test_sensitive_gate_is_opt_in(monkeypatch):
    high = _mem(sensitivity=Sensitivity.high)
    # Off by default: high sensitivity is allowed.
    assert _evaluate(_ranked(high)).records[0].decision is AdmissionDecision.ALLOW
    # Opt in → blocked.
    monkeypatch.setenv("MEMORYOPS_ADMISSION_BLOCK_SENSITIVE", "true")
    get_settings.cache_clear()
    assert _evaluate(_ranked(high)).records[0].decision is AdmissionDecision.BLOCK_SENSITIVE


def test_low_confidence_gate_is_opt_in(monkeypatch):
    weak = _ranked(_mem(), score=0.2)
    assert _evaluate(weak).records[0].decision is AdmissionDecision.ALLOW
    monkeypatch.setenv("MEMORYOPS_ADMISSION_MIN_SCORE", "0.5")
    get_settings.cache_clear()
    assert _evaluate(weak).records[0].decision is AdmissionDecision.BLOCK_LOW_CONFIDENCE


def test_shadow_mode_records_verdict_but_does_not_remove(monkeypatch):
    m = _mem()
    gov.set_consent(m, status=gov.ConsentStatus.withdrawn)
    monkeypatch.setenv("MEMORYOPS_ADMISSION_GATE", "false")
    get_settings.cache_clear()
    result = _evaluate(_ranked(m))
    # Verdict is still the block, but nothing is removed and nothing is "blocked".
    assert result.records[0].decision is AdmissionDecision.BLOCK_CONSENT_WITHDRAWN
    assert result.admitted  # composed anyway (observe-only)
    assert result.blocked_records == []
