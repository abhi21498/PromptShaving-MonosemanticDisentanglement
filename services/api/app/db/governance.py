"""Governance state on a memory: legal hold, consent, pins/protection (v0.10).

Like the v0.7 compaction tombstone (``entities.apply_compaction``) and the v0.6
lifecycle markers, governance state lives in the memory's ``metadata`` jsonb —
content-free, auditable, and persisted by both repository backends. This module
is the single source of truth for *reading and writing* that state so workers,
the policy/retention engine, and the API never hand-roll metadata keys.

Layout (all under ``metadata``)::

    metadata = {
      "pinned": bool,                      # user pin: exempt from decay/archive
      "protected": bool,                   # exempt from retention auto-deletion
      "governance": {
        "legal_hold": bool,                # fail-closed: blocks ALL forgetting
        "legal_hold_reason": str | None,
        "consent": {"status": "...", "captured_at": iso, "expires_at": iso|None},
        "retention": {"policy": str, "expires_at": iso|None, "evaluated_at": iso},
      },
    }

``pinned`` / ``protected`` stay at the top level for backward compatibility with
the v0.6 archive worker, which already reads ``metadata.pinned`` /
``metadata.protected``.

Invariant alignment: governance state is *advisory metadata that only ever makes
the system more conservative* — a hold blocks forgetting, consent withdrawal makes
a memory eligible for deletion. It never promotes or resurrects memory and never
bypasses the policy broker (CLAUDE.md invariant #5).
"""

from __future__ import annotations

from datetime import UTC, datetime

from .entities import StoredMemory

GOVERNANCE_META_KEY = "governance"


# ── consent ──────────────────────────────────────────────────────────────────
class ConsentStatus:
    granted = "granted"
    withdrawn = "withdrawn"
    expired = "expired"
    not_required = "not_required"

    ALL = frozenset({granted, withdrawn, expired, not_required})
    # Consent states that make a memory eligible for retention-driven deletion.
    REVOKED = frozenset({withdrawn, expired})


def _gov(memory: StoredMemory) -> dict:
    meta = memory.metadata.get(GOVERNANCE_META_KEY)
    return dict(meta) if isinstance(meta, dict) else {}


def _write_gov(memory: StoredMemory, gov: dict) -> None:
    # Copy-on-write so callers never mutate a shared dict in place.
    memory.metadata = dict(memory.metadata)
    memory.metadata[GOVERNANCE_META_KEY] = gov


def _iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.isoformat()


def _parse_dt(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts


# ── legal hold ───────────────────────────────────────────────────────────────
def is_legal_hold(memory: StoredMemory) -> bool:
    """True when a fail-closed legal hold is in force (blocks ALL forgetting)."""
    return bool(_gov(memory).get("legal_hold"))


def legal_hold_reason(memory: StoredMemory) -> str | None:
    val = _gov(memory).get("legal_hold_reason")
    return val if isinstance(val, str) and val else None


def set_legal_hold(
    memory: StoredMemory, *, on: bool, reason: str | None = None, now: datetime | None = None
) -> None:
    now = now or datetime.now(UTC)
    gov = _gov(memory)
    gov["legal_hold"] = bool(on)
    gov["legal_hold_reason"] = reason if on else None
    gov["legal_hold_updated_at"] = _iso(now)
    _write_gov(memory, gov)


# ── pins / protection ────────────────────────────────────────────────────────
def is_pinned(memory: StoredMemory) -> bool:
    """Pinned memory is exempt from decay and archive (user wants it kept fresh)."""
    return bool(memory.metadata.get("pinned"))


def is_protected(memory: StoredMemory) -> bool:
    """Protected memory is exempt from retention-driven auto-deletion."""
    return bool(memory.metadata.get("protected"))


def set_pinned(memory: StoredMemory, *, on: bool) -> None:
    memory.metadata = dict(memory.metadata)
    memory.metadata["pinned"] = bool(on)


def set_protected(memory: StoredMemory, *, on: bool) -> None:
    memory.metadata = dict(memory.metadata)
    memory.metadata["protected"] = bool(on)


def is_retention_exempt(memory: StoredMemory) -> bool:
    """Any override that blocks retention-driven deletion: hold, pin, or protect."""
    return is_legal_hold(memory) or is_pinned(memory) or is_protected(memory)


def retention_blockers(memory: StoredMemory) -> list[str]:
    """Admin-readable list of why a memory is exempt from retention deletion."""
    blockers: list[str] = []
    if is_legal_hold(memory):
        blockers.append("legal_hold")
    if is_pinned(memory):
        blockers.append("pinned")
    if is_protected(memory):
        blockers.append("protected")
    return blockers


# ── consent ──────────────────────────────────────────────────────────────────
def consent_status(memory: StoredMemory, *, now: datetime | None = None) -> str:
    """Effective consent status, resolving an elapsed ``expires_at`` to expired.

    Memory with no recorded consent is treated as ``granted`` (capture default),
    so legacy/pre-v0.10 memory is never made eligible for deletion by surprise.
    """
    now = now or datetime.now(UTC)
    consent = _gov(memory).get("consent")
    if not isinstance(consent, dict):
        return ConsentStatus.granted
    status = consent.get("status", ConsentStatus.granted)
    if status == ConsentStatus.withdrawn:
        return ConsentStatus.withdrawn
    expires_at = _parse_dt(consent.get("expires_at"))
    if expires_at is not None and now >= expires_at:
        return ConsentStatus.expired
    return status if status in ConsentStatus.ALL else ConsentStatus.granted


def set_consent(
    memory: StoredMemory,
    *,
    status: str,
    expires_at: datetime | None = None,
    now: datetime | None = None,
) -> None:
    if status not in ConsentStatus.ALL:
        raise ValueError(f"unknown consent status: {status!r}")
    now = now or datetime.now(UTC)
    gov = _gov(memory)
    gov["consent"] = {
        "status": status,
        "captured_at": _iso(now),
        "expires_at": _iso(expires_at) if expires_at else None,
    }
    _write_gov(memory, gov)


# ── retention bookkeeping (computed window the worker stamps) ─────────────────
def retention_state(memory: StoredMemory) -> dict:
    state = _gov(memory).get("retention")
    return dict(state) if isinstance(state, dict) else {}


def set_retention(
    memory: StoredMemory,
    *,
    policy: str,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(UTC)
    gov = _gov(memory)
    gov["retention"] = {
        "policy": policy,
        "expires_at": _iso(expires_at) if expires_at else None,
        "evaluated_at": _iso(now),
    }
    _write_gov(memory, gov)


def public_governance(memory: StoredMemory, *, now: datetime | None = None) -> dict:
    """Content-free governance summary for admin/API surfaces (no memory text)."""
    return {
        "legal_hold": is_legal_hold(memory),
        "legal_hold_reason": legal_hold_reason(memory),
        "pinned": is_pinned(memory),
        "protected": is_protected(memory),
        "consent_status": consent_status(memory, now=now),
        "retention": retention_state(memory),
    }
