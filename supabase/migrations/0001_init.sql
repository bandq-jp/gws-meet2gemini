-- enable uuid generation
create extension if not exists pgcrypto;

-- meeting_documents table
create table if not exists public.meeting_documents (
  id uuid primary key default gen_random_uuid(),
  doc_id text not null,
  title text,
  meeting_datetime text,
  organizer_email text not null,
  organizer_name text,
  document_url text,
  invited_emails text[] default '{}',
  text_content text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- unique constraint to avoid duplicates per organizer
create unique index if not exists meeting_unique_doc_per_org
  on public.meeting_documents (doc_id, organizer_email);

-- structured_outputs table
create table if not exists public.structured_outputs (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid not null references public.meeting_documents(id) on delete cascade,
  data jsonb not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create unique index if not exists structured_unique_meeting
  on public.structured_outputs (meeting_id);

-- trigger to update updated_at
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_updated_at_meeting on public.meeting_documents;
create trigger trg_updated_at_meeting
before update on public.meeting_documents
for each row execute procedure set_updated_at();

drop trigger if exists trg_updated_at_structured on public.structured_outputs;
create trigger trg_updated_at_structured
before update on public.structured_outputs
for each row execute procedure set_updated_at();
