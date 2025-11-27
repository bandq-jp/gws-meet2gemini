-- SEO記事本体を永続化するテーブルを追加し、Canvas/差分編集のソース・オブ・トゥルースをDBに寄せる

create table if not exists public.marketing_articles (
  id text primary key,
  conversation_id text not null references public.marketing_conversations(id) on delete cascade,
  title text,
  outline text,
  body_html text,
  language text default 'ja',
  version integer not null default 1 check (version > 0),
  status text not null default 'draft' check (status in ('draft', 'in_progress', 'published', 'archived')),
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists marketing_articles_conversation_id_idx
  on public.marketing_articles(conversation_id);
create index if not exists marketing_articles_updated_at_idx
  on public.marketing_articles(updated_at desc);

drop trigger if exists trg_updated_at_marketing_articles on public.marketing_articles;
create trigger trg_updated_at_marketing_articles
before update on public.marketing_articles
for each row execute procedure set_updated_at();

alter table public.marketing_articles enable row level security;

-- Service role (サーバー側FastAPI/Agents) がフルアクセスできるようにする
drop policy if exists "service role full access marketing_articles" on public.marketing_articles;
create policy "service role full access marketing_articles"
  on public.marketing_articles
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');
