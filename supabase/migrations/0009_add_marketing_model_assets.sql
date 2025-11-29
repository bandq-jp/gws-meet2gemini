-- Model asset presets for marketing ChatKit (shared across organization)

create table if not exists public.marketing_model_assets (
  id text primary key,
  name text not null,
  description text,
  base_model text not null default 'gpt-5.1',
  reasoning_effort text not null default 'high' check (reasoning_effort in ('low', 'medium', 'high')),
  verbosity text not null default 'medium' check (verbosity in ('short', 'medium', 'long')),
  enable_web_search boolean not null default true,
  enable_code_interpreter boolean not null default true,
  enable_ga4 boolean not null default true,
  enable_gsc boolean not null default true,
  enable_ahrefs boolean not null default true,
  enable_wordpress boolean not null default true,
  system_prompt_addition text default null,
  metadata jsonb default '{}'::jsonb,
  created_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists marketing_model_assets_created_at_idx
  on public.marketing_model_assets(created_at desc);

drop trigger if exists trg_updated_at_marketing_model_assets on public.marketing_model_assets;
create trigger trg_updated_at_marketing_model_assets
before update on public.marketing_model_assets
for each row execute procedure set_updated_at();

alter table public.marketing_model_assets enable row level security;

-- service_role (=FastAPI/Agents) full access
drop policy if exists "service role full access marketing_model_assets" on public.marketing_model_assets;
create policy "service role full access marketing_model_assets"
  on public.marketing_model_assets
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

-- seed default "standard" preset to mirror existing behavior
insert into public.marketing_model_assets (
  id, name, description, base_model, reasoning_effort, verbosity,
  enable_web_search, enable_code_interpreter, enable_ga4, enable_gsc, enable_ahrefs, enable_wordpress,
  system_prompt_addition, metadata, created_by
) values (
  'standard',
  'スタンダード',
  '既定のマーケティングエージェント設定（GPT-5.1、高推論、Web検索+コード+各MCP有効）',
  'gpt-5.1',
  'high',
  'medium',
  true, true, true, true, true, true,
  null,
  '{}'::jsonb,
  'system'
)
on conflict (id) do nothing;
