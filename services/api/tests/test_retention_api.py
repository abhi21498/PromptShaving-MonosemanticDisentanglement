"""Retention + legal hold + consent API (v0.10, ADR-013).

Covers the /api/retention surface: setting governance flags, recording consent,
listing policy packs, and the read-only retention-decision preview. Every
mutation is tenant-scoped and audited; reads never leak memory content.
"""

from __future__ import annotations

from app.db.entities import StoredMemory
from app.schemas.memory import MemoryType, Sensitivity, Source, Status


def _seed(repo, *, tenant="t1", user="u1", sensitivity=Sensitivity.low, age_days=0,
          content="prefers dark mode") -> StoredMemory:
    from datetime import UTC, datetime, timedelta

    created = datetime.now(UTC) - timedelta(days=age_days)
    m = StoredMemory(
        tenant_id=tenant, user_id=user, memory_type=MemoryType.preference,
        content=content, importance=5, confidence=0.8, sensitivity=sensitivity,
        status=Status.active, source=Source(kind="chat", excerpt=content),
        created_at=created, updated_at=created,
    )
    return repo.create_memory(m)


def _body(repo_id, **extra):
    return {"tenant_id": "t1", "user_id": "u1", "memory_id": repo_id, **extra}


def test_set_and_release_legal_hold(api_client):
    client, repo = api_client
    m = _seed(repo)
    r = client.post("/api/retention/legal-hold", json=_body(m.id, on=True, reason="hold"))
    assert r.status_code == 200
    assert r.json()["governance"]["legal_hold"] is True
    assert "memory_legal_hold_set" in {e.action for e in repo.list_audit("t1", "u1")}

    r2 = client.post("/api/retention/legal-hold", json=_body(m.id, on=False))
    assert r2.json()["governance"]["legal_hold"] is False


def test_pin_and_protect(api_client):
    client, repo = api_client
    m = _seed(repo)
    assert client.post("/api/retention/pin", json=_body(m.id, on=True)).json()[
        "governance"]["pinned"] is True
    assert client.post("/api/retention/protect", json=_body(m.id, on=True)).json()[
        "governance"]["protected"] is True


def test_consent_update_and_validation(api_client):
    client, repo = api_client
    m = _seed(repo)
    ok = client.post("/api/retention/consent", json=_body(m.id, status="withdrawn"))
    assert ok.status_code == 200
    assert ok.json()["governance"]["consent_status"] == "withdrawn"

    bad = client.post("/api/retention/consent", json=_body(m.id, status="bogus"))
    assert bad.status_code == 422


def test_missing_memory_is_404(api_client):
    client, _ = api_client
    r = client.post("/api/retention/legal-hold", json=_body("nope", on=True))
    assert r.status_code == 404


def test_list_policies(api_client):
    client, _ = api_client
    r = client.get("/api/retention/policies")
    assert r.status_code == 200
    names = {p["name"] for p in r.json()["policies"]}
    assert {"default", "strict", "extended"} <= names


def test_decisions_preview_is_read_only_and_content_free(api_client):
    client, repo = api_client
    expired = _seed(repo, sensitivity=Sensitivity.high, age_days=500, content="old secret")
    _seed(repo, age_days=1, content="fresh")

    r = client.get("/api/retention/decisions?tenant_id=t1&user_id=u1&policy=default")
    assert r.status_code == 200
    body = r.json()
    assert body["scanned"] == 2
    assert body["summary"].get("expired", 0) >= 1
    # Read-only: nothing was deleted.
    assert repo.get_memory("t1", "u1", expired.id).status == Status.active
    # Content-free.
    assert "old secret" not in r.text


def test_decisions_are_tenant_scoped(api_client):
    client, repo = api_client
    _seed(repo, tenant="t1", sensitivity=Sensitivity.high, age_days=500)
    _seed(repo, tenant="t2", sensitivity=Sensitivity.high, age_days=500)
    r = client.get("/api/retention/decisions?tenant_id=t1&user_id=u1")
    assert r.json()["scanned"] == 1


def test_memory_governance_detail(api_client):
    client, repo = api_client
    m = _seed(repo, sensitivity=Sensitivity.high, age_days=500)
    r = client.get(f"/api/retention/memory/{m.id}?tenant_id=t1&user_id=u1")
    assert r.status_code == 200
    assert r.json()["retention_decision"]["outcome"] == "expired"
