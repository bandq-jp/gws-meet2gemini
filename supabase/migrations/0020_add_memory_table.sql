-- Migration: Add marketing_memories table for ADK Memory Service
-- Uses pgvector for semantic search with Gemini embeddings

-- Enable pgvector extension (Supabase has this built-in)
create extension if not exists vector;

-- Marketing memories table
-- Stores conversation events with embeddings for semantic search
create table if not exists marketing_memories (
  id uuid primary key default gen_random_uuid(),

  -- Scope identifiers (required for ADK MemoryService)
  app_name text not null default 'marketing_ai',
  user_id text not null,
  user_email text,

  -- Session/conversation reference
  session_id text,
  conversation_id text references marketing_conversations(id) on delete set null,

  -- Event data
  event_id text,
  author text,  -- 'user' or 'model' or agent name
  event_timestamp timestamptz,

  -- Content
  content_text text not null,

  -- Vector embedding for semantic search
  -- gemini-embedding-001: supports 768 to 3072 dimensions (Matryoshka)
  -- Using 768 for storage efficiency while maintaining quality
  embedding vector(768),

  -- Additional metadata
  metadata jsonb default '{}'::jsonb,

  -- Timestamps
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Indexes for efficient querying
-- Basic lookup by app + user
create index if not exists idx_memories_app_user
  on marketing_memories(app_name, user_id);

-- Lookup by conversation
create index if not exists idx_memories_conversation
  on marketing_memories(conversation_id);

-- Lookup by session
create index if not exists idx_memories_session
  on marketing_memories(session_id);

-- Vector similarity search index (IVFFlat for approximate nearest neighbor)
-- lists=100 is good for up to ~100k records; increase for larger datasets
create index if not exists idx_memories_embedding
  on marketing_memories using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Full-text search index (fallback for keyword search)
-- Note: Using 'simple' config as 'japanese' is not available in Supabase
-- Primary search uses pgvector semantic search anyway
create index if not exists idx_memories_content_fts
  on marketing_memories using gin(to_tsvector('simple', content_text));

-- RPC function for semantic search
-- Uses cosine distance for similarity (lower = more similar)
create or replace function search_memories_by_embedding(
  query_embedding vector(768),
  match_app_name text default 'marketing_ai',
  match_user_id text default null,
  match_count int default 5,
  similarity_threshold float default 0.3
)
returns table (
  id uuid,
  content_text text,
  author text,
  event_timestamp timestamptz,
  session_id text,
  conversation_id text,
  metadata jsonb,
  created_at timestamptz,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    m.id,
    m.content_text,
    m.author,
    m.event_timestamp,
    m.session_id,
    m.conversation_id,
    m.metadata,
    m.created_at,
    -- Cosine similarity: 1 - cosine_distance
    (1 - (m.embedding <=> query_embedding))::float as similarity
  from marketing_memories m
  where m.app_name = match_app_name
    and (match_user_id is null or m.user_id = match_user_id)
    and m.embedding is not null
    -- Filter by similarity threshold
    and (1 - (m.embedding <=> query_embedding)) >= similarity_threshold
  order by m.embedding <=> query_embedding  -- Ascending = closer
  limit match_count;
end;
$$;

-- Trigger to update updated_at
create or replace function update_memories_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trigger_memories_updated_at
  before update on marketing_memories
  for each row
  execute function update_memories_updated_at();

-- Comment on table
comment on table marketing_memories is 'ADK Memory Service storage with pgvector semantic search';
comment on column marketing_memories.embedding is 'Gemini embedding vector (768 dimensions)';
