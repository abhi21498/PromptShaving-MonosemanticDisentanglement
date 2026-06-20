-- 003_indexes_rls.sql — indexes and row-level-security scaffolding

create index if not exists idx_memory_user_status
  on memory_records(tenant_id, user_id, status);
create index if not exists idx_memory_type
  on memory_records(memory_type);
create index if not exists idx_memory_created_at
  on memory_records(created_at);
create index if not exists idx_audit_tenant_created
  on memory_audit_logs(tenant_id, created_at desc);

-- pgvector ANN index (cosine). Built after data exists in production; safe to create empty.
create index if not exists idx_memory_embedding
  on memory_records using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Row-Level Security: enabled now (RLS-ready). Enforcing policies is Phase 4.
alter table memory_records   enable row level security;
alter table memory_audit_logs enable row level security;

-- Example tenant-isolation policy (commented until the app sets app.tenant_id per session):
-- create policy tenant_isolation on memory_records
--   using (tenant_id = current_setting('app.tenant_id')::uuid);
