"""Retention policy engine (v0.10, ADR-013).

Deterministic, config-driven retention. A **retention policy pack** maps a
memory's sensitivity tier to a retention window (in days). Evaluating a memory
against a pack — together with its legal-hold / pin / protection overrides and
consent state — yields an admin-readable :class:`RetentionDecision` explaining
*why* the memory is retained, held, expired, or had consent revoked.

Design rules:
  * No DB and no API keys required — packs are defined in code, selected by name,
    so the default path works exactly like the rest of the stub-first system.
  * The engine only ever proposes the *conservative* outcome: a memory becomes
    eligible for deletion only when nothing holds it and either its window has
    elapsed or consent was revoked. Overrides always win.
  * The engine decides eligibility; it never deletes. The retention worker acts
    on decisions and the deletion guarantee + audit trail stay authoritative.

See docs/retention-policies.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum

from ..db import governance as gov
from ..db.entities import StoredMemory
from ..schemas.memory import Sensitivity


class RetentionOutcome(str, Enum):
    retain = "retain"  # within window, consent valid → keep
    expired = "expired"  # retention window elapsed → eligible for deletion
    consent_revoked = "consent_revoked"  # consent withdrawn/expired → eligible
    held = "held"  # legal hold / pin / protection blocks deletion


# Eligible-for-deletion outcomes (the worker acts only on these).
ELIGIBLE_OUTCOMES = frozenset({RetentionOutcome.expired, RetentionOutcome.consent_revoked})


@dataclass(frozen=True)
class RetentionPolicy:
    """A named retention pack: sensitivity tier → retention window in days.

    ``windows`` is keyed by :class:`Sensitivity` value. A window of ``None`` means
    "retain indefinitely" (no time-based expiry) for that tier.
    """

    name: str
    description: str
    windows: dict[str, int | None]

    def window_days(self, sensitivity: Sensitivity) -> int | None:
        return self.windows.get(sensitivity.value, None)


# ── built-in policy packs ─────────────────────────────────────────────────────
# Higher sensitivity → shorter retention. Tunable without touching the engine.
DEFAULT_POLICY = RetentionPolicy(
    name="default",
    description="Balanced retention: high-sensitivity memory expires soonest.",
    windows={Sensitivity.low.value: 365, Sensitivity.medium.value: 180, Sensitivity.high.value: 90},
)

STRICT_POLICY = RetentionPolicy(
    name="strict",
    description="Aggressive minimization for regulated/short-retention tenants.",
    windows={Sensitivity.low.value: 180, Sensitivity.medium.value: 90, Sensitivity.high.value: 30},
)

EXTENDED_POLICY = RetentionPolicy(
    name="extended",
    description="Long-lived knowledge retention; only high sensitivity expires.",
    windows={
        Sensitivity.low.value: None,
        Sensitivity.medium.value: 365,
        Sensitivity.high.value: 180,
    },
)

_REGISTRY: dict[str, RetentionPolicy] = {
    p.name: p for p in (DEFAULT_POLICY, STRICT_POLICY, EXTENDED_POLICY)
}


def get_policy(name: str | None) -> RetentionPolicy:
    """Resolve a policy pack by name, falling back to the default pack."""
    if not name:
        return DEFAULT_POLICY
    return _REGISTRY.get(name, DEFAULT_POLICY)


def available_policies() -> list[RetentionPolicy]:
    return list(_REGISTRY.values())


# ── decisions ─────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RetentionDecision:
    """Admin-readable outcome of evaluating one memory against a policy pack.

    Content-free: ids, the policy name, the outcome, the computed expiry, the
    blocking overrides, and a human reason — never the memory's text.
    """

    memory_id: str
    policy: str
    outcome: RetentionOutcome
    sensitivity: str
    consent_status: str
    age_days: int
    window_days: int | None
    retention_expires_at: datetime | None
    blocked_by: list[str]
    reason: str

    @property
    def eligible_for_deletion(self) -> bool:
        return self.outcome in ELIGIBLE_OUTCOMES

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "policy": self.policy,
            "outcome": self.outcome.value,
            "sensitivity": self.sensitivity,
            "consent_status": self.consent_status,
            "age_days": self.age_days,
            "window_days": self.window_days,
            "retention_expires_at": (
                self.retention_expires_at.isoformat() if self.retention_expires_at else None
            ),
            "blocked_by": list(self.blocked_by),
            "reason": self.reason,
            "eligible_for_deletion": self.eligible_for_deletion,
        }


def _age_days(memory: StoredMemory, now: datetime) -> int:
    created = memory.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return max(0, (now - created).days)


def evaluate(
    memory: StoredMemory, *, now: datetime | None = None, policy: RetentionPolicy | None = None
) -> RetentionDecision:
    """Evaluate one memory against a retention policy pack.

    Precedence (most conservative wins):
      1. legal hold / pin / protection  → ``held`` (never eligible);
      2. consent withdrawn or expired   → ``consent_revoked`` (eligible now);
      3. retention window elapsed       → ``expired`` (eligible);
      4. otherwise                      → ``retain`` (with computed expiry).
    """
    now = now or datetime.now(UTC)
    policy = policy or DEFAULT_POLICY
    age = _age_days(memory, now)
    window = policy.window_days(memory.sensitivity)
    consent = gov.consent_status(memory, now=now)
    blockers = gov.retention_blockers(memory)

    created = memory.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    expires_at = created + timedelta(days=window) if window is not None else None

    if blockers:
        return RetentionDecision(
            memory_id=memory.id, policy=policy.name, outcome=RetentionOutcome.held,
            sensitivity=memory.sensitivity.value, consent_status=consent, age_days=age,
            window_days=window, retention_expires_at=expires_at, blocked_by=blockers,
            reason=f"retention blocked by {', '.join(blockers)}",
        )

    if consent in gov.ConsentStatus.REVOKED:
        return RetentionDecision(
            memory_id=memory.id, policy=policy.name, outcome=RetentionOutcome.consent_revoked,
            sensitivity=memory.sensitivity.value, consent_status=consent, age_days=age,
            window_days=window, retention_expires_at=expires_at, blocked_by=[],
            reason=f"consent {consent}; eligible for deletion",
        )

    if window is not None and age >= window:
        return RetentionDecision(
            memory_id=memory.id, policy=policy.name, outcome=RetentionOutcome.expired,
            sensitivity=memory.sensitivity.value, consent_status=consent, age_days=age,
            window_days=window, retention_expires_at=expires_at, blocked_by=[],
            reason=f"retention window of {window}d elapsed (age {age}d)",
        )

    detail = "no time-based expiry" if window is None else f"expires in {window - age}d"
    return RetentionDecision(
        memory_id=memory.id, policy=policy.name, outcome=RetentionOutcome.retain,
        sensitivity=memory.sensitivity.value, consent_status=consent, age_days=age,
        window_days=window, retention_expires_at=expires_at, blocked_by=[],
        reason=f"within retention policy '{policy.name}' ({detail})",
    )
