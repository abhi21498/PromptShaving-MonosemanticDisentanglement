-- 002_core_tables.sql — tenants, users, memory records, audit, feedback, settings

create table if not exists tenants (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  created_at timestamptz default now()
);

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  external_id text,                       -- stable app-facing id (e.g. "user_demo")
  email text not null,
  role text not null default 'user' check (role in ('user','approver','admin','auditor')),
  created_at timestamptz default now(),
  unique (tenant_id, external_id)
);

create table if not exists memory_records (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  user_id uuid not null references users(id),

  memory_type text not null check (
    memory_type in (
      'episodic','semantic','procedural','project',
      'knowledge','system','constraint','preference','workflow'
    )
  ),

  content text not null,
  normalized_content text,
  embedding vector(1536),

  importance int not null default 5 check (importance between 0 and 10),
  confidence real not null default 0.7 check (confidence >= 0 and confidence <= 1),
  sensitivity text not null default 'low' check (sensitivity in ('low','medium','high')),
  status text not null default 'active' check (
    status in ('active','pending','archived','deleted','rejected','blocked')
  ),

  source jsonb not null,                  -- provenance (invariant #3): NOT NULL
  metadata jsonb default '{}'::jsonb,

  weight real not null default 1.0,
  reinforcement_count int not null default 0,

  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  archived_at timestamptz,
  deleted_at timestamptz
);

create table if not exists memory_audit_logs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  user_id uuid,
  memory_id uuid,
  action text not null,
  reason text not null,
  trace_id text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists memory_feedback (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  user_id uuid not null,
  memory_id uuid references memory_records(id),
  feedback_type text not null check (
    feedback_type in ('helpful','wrong','outdated','sensitive','not_relevant')
  ),
  comment text,
  created_at timestamptz default now()
);

create table if not exists memory_settings (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  user_id uuid not null,
  memory_enabled boolean default true,
  require_approval_for_sensitive boolean default true,
  temporary_chat boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (tenant_id, user_id)
);
