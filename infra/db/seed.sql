-- seed.sql — demo tenants/users/settings for the demo script

insert into tenants (slug, name) values
  ('tenant_demo', 'Demo Tenant'),
  ('tenant_acme', 'Acme Corp')
on conflict (slug) do nothing;

insert into users (tenant_id, external_id, email, role)
select t.id, 'user_demo', 'demo@memoryops.ai', 'user'
from tenants t where t.slug = 'tenant_demo'
on conflict (tenant_id, external_id) do nothing;

insert into users (tenant_id, external_id, email, role)
select t.id, 'admin_demo', 'admin@memoryops.ai', 'admin'
from tenants t where t.slug = 'tenant_demo'
on conflict (tenant_id, external_id) do nothing;

insert into users (tenant_id, external_id, email, role)
select t.id, 'user_acme', 'user@acme.example', 'user'
from tenants t where t.slug = 'tenant_acme'
on conflict (tenant_id, external_id) do nothing;

insert into memory_settings (tenant_id, user_id, memory_enabled, require_approval_for_sensitive, temporary_chat)
select u.tenant_id, u.id, true, true, false
from users u
on conflict (tenant_id, user_id) do nothing;
