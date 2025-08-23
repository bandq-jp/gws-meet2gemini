-- AI使用量ログテーブルの追加
-- 各Gemini API呼び出しのトークン使用量を記録する

create table if not exists public.ai_usage_logs (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid references public.meeting_documents(id) on delete set null,
  group_name text,                    -- 例: "転職活動状況・エージェント関連"
  model text not null,                -- 例: "gemini-2.5-pro"
  prompt_token_count int,             -- 入力トークン数
  candidates_token_count int,         -- 出力トークン数
  cached_content_token_count int,     -- キャッシュ命中トークン数（ある場合）
  total_token_count int,              -- 合計トークン数
  finish_reason text,                 -- 生成完了理由
  response_chars int,                 -- 返却テキストの文字数（品質/コスト相関分析用）
  latency_ms int,                     -- レスポンス時間（ミリ秒）
  usage_raw jsonb,                    -- usage_metadataの生ログ（将来の拡張用）
  created_at timestamptz not null default now()
);

-- インデックス作成
create index if not exists ai_usage_logs_meeting_id_idx on public.ai_usage_logs(meeting_id);
create index if not exists ai_usage_logs_created_at_idx on public.ai_usage_logs(created_at desc);
create index if not exists ai_usage_logs_model_idx on public.ai_usage_logs(model);

-- RLSポリシー設定
alter table public.ai_usage_logs enable row level security;

-- 認証されたユーザーによる読み取りを許可
create policy "Allow authenticated read access to ai_usage_logs" on public.ai_usage_logs
  for select using (auth.role() = 'authenticated');

-- サービスロールによる全操作を許可  
create policy "Allow service role full access to ai_usage_logs" on public.ai_usage_logs
  for all using (auth.role() = 'service_role');