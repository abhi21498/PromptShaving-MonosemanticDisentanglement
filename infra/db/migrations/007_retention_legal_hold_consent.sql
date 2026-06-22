-- 007_retention_legal_hold_consent.sql — retention policies + legal hold +
-- consent-aware memory (v0.10, ADR-013).
--
-- Governance state is metadata-driven (like the v0.7 compaction tombstone and the
-- v0.6 lifecycle markers): it lives in memory_records.metadata, so no destructive
-- schema change is required and both repository backends round-trip it. This
-- migration adds indexes so the retention worker and admin/API surfaces can find
-- governed rows efficiently, and documents the metadata contract.
--
-- metadata layout (see services/api/app/db/governance.py):
--   metadata.pinned                 bool   -- exempt from decay/archive
--   metadata.protected              bool   -- exempt from retention auto-deletion
--   metadata.governance.legal_hold  bool   -- fail-closed: blocks ALL forgetting
--   metadata.governance.legal_hold_reason   text
--   metadata.governance.consent     {status, captured_at, expires_at}
--   metadata.governance.retention   {policy, expires_at, evaluated_at}
--
-- Legal hold is enforced in application code (retention/decay/archive/compaction
-- workers + the delete route) AND surfaced here as a fast partial index. It is a
-- compliance preservation control, NOT crypto-shred — content under hold is
-- deliberately retained.

-- Fast lookup of memory currently on legal hold (compliance / discovery).
create index if not exists idx_memory_legal_hold
on memory_records (tenant_id, user_id)
where (metadata #>> '{governance,legal_hold}') = 'true';

-- Fast lookup of memory whose consent has been withdrawn (retention-eligible).
create index if not exists idx_memory_consent_withdrawn
on memory_records (tenant_id, user_id)
where (metadata #>> '{governance,consent,status}') = 'withdrawn';

-- General containment queries over governance metadata (pins/protection/policy).
create index if not exists idx_memory_metadata_gin
on memory_records using gin (metadata jsonb_path_ops);

comment on column memory_records.metadata is
  'Content-free bookkeeping: lifecycle markers (v0.6), compaction tombstone (v0.7), '
  'and governance state (v0.10: legal_hold, consent, retention, pinned, protected).';
