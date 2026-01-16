-- Add chat sharing support to marketing_conversations
-- Allows authenticated users to view shared conversations in read-only mode

-- Add sharing columns
alter table if exists public.marketing_conversations
  add column if not exists is_shared boolean not null default false,
  add column if not exists shared_at timestamptz,
  add column if not exists shared_by_email text,
  add column if not exists shared_by_clerk_id text;

-- Index for efficient shared chat lookup
create index if not exists marketing_conversations_is_shared_idx
  on public.marketing_conversations(is_shared) where is_shared = true;

-- Add comments for documentation
comment on column public.marketing_conversations.is_shared is
  'When true, any authenticated user can view this conversation in read-only mode';
comment on column public.marketing_conversations.shared_at is
  'Timestamp when the conversation was first shared';
comment on column public.marketing_conversations.shared_by_email is
  'Email of the user who enabled sharing';
comment on column public.marketing_conversations.shared_by_clerk_id is
  'Clerk ID of the user who enabled sharing';
