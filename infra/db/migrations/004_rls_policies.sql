-- 004_rls_policies.sql — enforce Row-Level Security (v0.3)
--
-- Migration 003 enabled RLS on memory_records / memory_audit_logs but left the
-- policies commented out. This migration enforces tenant isolation at the
-- database layer (defense in depth, ADR-006): even a bug in application-level
-- filtering cannot leak one tenant's memories to another.
--
-- Model: RLS is TENANT-scoped. The repository sets a transaction-local GUC
-- (app.tenant_id) on every session; policies compare it to the row's tenant_id.
-- Per-USER isolation stays in application SQL (every query also filters user_id),
-- so tenant-wide admin/metrics reads still work under RLS.
--
-- FORCE is used so the policies apply even to the table owner — this makes the
-- guarantee provable in tests/check_rls_policies.py regardless of connection role.

-- ── memory_records ───────────────────────────────────────────────────────────
alter table memory_records enable row level security;
alter table memory_records force row level security;

drop policy if exists memory_records_tenant_isolation on memory_records;
create policy memory_records_tenant_isolation on memory_records
  using (tenant_id::text = current_setting('app.tenant_id', true))
  with check (tenant_id::text = current_setting('app.tenant_id', true));

-- ── memory_audit_logs ────────────────────────────────────────────────────────
alter table memory_audit_logs enable row level security;
alter table memory_audit_logs force row level security;

drop policy if exists memory_audit_logs_tenant_isolation on memory_audit_logs;
create policy memory_audit_logs_tenant_isolation on memory_audit_logs
  using (tenant_id::text = current_setting('app.tenant_id', true))
  with check (tenant_id::text = current_setting('app.tenant_id', true));

-- ── memory_feedback ──────────────────────────────────────────────────────────
alter table memory_feedback enable row level security;
alter table memory_feedback force row level security;

drop policy if exists memory_feedback_tenant_isolation on memory_feedback;
create policy memory_feedback_tenant_isolation on memory_feedback
  using (tenant_id::text = current_setting('app.tenant_id', true))
  with check (tenant_id::text = current_setting('app.tenant_id', true));

-- ── memory_settings ──────────────────────────────────────────────────────────
alter table memory_settings enable row level security;
alter table memory_settings force row level security;

drop policy if exists memory_settings_tenant_isolation on memory_settings;
create policy memory_settings_tenant_isolation on memory_settings
  using (tenant_id::text = current_setting('app.tenant_id', true))
  with check (tenant_id::text = current_setting('app.tenant_id', true));
