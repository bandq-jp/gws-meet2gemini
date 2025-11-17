-- Marketing chat data models (conversations + messages) for the SEO assistant

create table if not exists public.marketing_conversations (
  id text primary key,
  slug text unique,
  title text not null,
  description text,
  marketing_goal text,
  target_urls text[] default '{}',
  target_keywords text[] default '{}',
  research_scope jsonb default '{}'::jsonb,
  owner_email text,
  owner_clerk_id text,
  status text not null default 'active' check (status in ('active', 'archived', 'closed')),
  latest_summary text,
  pinned_insights jsonb default '[]'::jsonb,
  metadata jsonb default '{}'::jsonb,
  last_message_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists marketing_conversations_owner_email_idx
  on public.marketing_conversations(owner_email);
create index if not exists marketing_conversations_status_idx
  on public.marketing_conversations(status);
create index if not exists marketing_conversations_created_at_idx
  on public.marketing_conversations(created_at desc);

drop trigger if exists trg_updated_at_marketing_conversations on public.marketing_conversations;
create trigger trg_updated_at_marketing_conversations
before update on public.marketing_conversations
for each row execute procedure set_updated_at();

create table if not exists public.marketing_messages (
  id text primary key,
  conversation_id text not null references public.marketing_conversations(id) on delete cascade,
  role text not null check (role in ('system', 'user', 'assistant', 'tool', 'progress', 'event')),
  message_type text not null default 'content',
  content jsonb not null default '{}'::jsonb,
  plain_text text,
  progress_label text,
  progress_value numeric,
  model text,
  tool_calls jsonb,
  metrics jsonb,
  attachments jsonb,
  created_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists marketing_messages_conversation_id_idx
  on public.marketing_messages(conversation_id);
create index if not exists marketing_messages_created_at_idx
  on public.marketing_messages(created_at);
create index if not exists marketing_messages_role_idx
  on public.marketing_messages(role);

drop trigger if exists trg_updated_at_marketing_messages on public.marketing_messages;
create trigger trg_updated_at_marketing_messages
before update on public.marketing_messages
for each row execute procedure set_updated_at();

create table if not exists public.marketing_attachments (
  id text primary key,
  conversation_id text not null references public.marketing_conversations(id) on delete cascade,
  owner_email text,
  filename text,
  mime_type text,
  size_bytes bigint,
  storage_metadata jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists marketing_attachments_conversation_id_idx
  on public.marketing_attachments(conversation_id);

alter table public.marketing_conversations enable row level security;
alter table public.marketing_messages enable row level security;
alter table public.marketing_attachments enable row level security;

-- Service role keeps full access for server-side FastAPI integration
drop policy if exists "service role full access marketing_conversations" on public.marketing_conversations;
create policy "service role full access marketing_conversations"
  on public.marketing_conversations
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

drop policy if exists "service role full access marketing_messages" on public.marketing_messages;
create policy "service role full access marketing_messages"
  on public.marketing_messages
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

drop policy if exists "service role full access marketing_attachments" on public.marketing_attachments;
create policy "service role full access marketing_attachments"
  on public.marketing_attachments
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');
