-- カスタムスキーマ機能のためのテーブル作成
-- ユーザーがデフォルトスキーマをカスタマイズして保存・使用できるようにする

-- カスタムスキーマの基本情報テーブル
create table if not exists public.custom_schemas (
  id uuid primary key default gen_random_uuid(),
  name text not null, -- スキーマ名（ユーザー定義）
  description text, -- スキーマの説明
  is_default boolean default false, -- デフォルトスキーマかどうか
  is_active boolean default true, -- アクティブな状態かどうか
  created_by text, -- 作成者（将来的にユーザー管理機能追加時に使用）
  base_schema_version text, -- ベースとなったスキーマのバージョン（将来的なスキーマ変更追跡用）
  schema_groups jsonb default '[]'::jsonb, -- グループ情報を保存
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- スキーマフィールド定義テーブル
create table if not exists public.schema_fields (
  id uuid primary key default gen_random_uuid(),
  custom_schema_id uuid not null references public.custom_schemas(id) on delete cascade,
  field_key text not null, -- フィールドのキー（例: transfer_activity_status）
  field_label text not null, -- フィールドの表示ラベル
  field_description text, -- フィールドの説明
  field_type text not null check (field_type in ('string', 'number', 'integer', 'array', 'boolean', 'object')), -- データ型
  is_required boolean default false, -- 必須フィールドかどうか
  array_item_type text, -- 配列の場合の要素の型
  group_name text, -- どのグループに属するか
  display_order integer default 0, -- 表示順序
  validation_rules jsonb default '{}'::jsonb, -- バリデーションルール（min、max等）
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- フィールドの列挙型選択肢テーブル
create table if not exists public.field_enum_options (
  id uuid primary key default gen_random_uuid(),
  schema_field_id uuid not null references public.schema_fields(id) on delete cascade,
  option_value text not null, -- 選択肢の値
  option_label text, -- 選択肢の表示ラベル（値と異なる場合）
  display_order integer default 0, -- 選択肢の表示順序
  created_at timestamptz default now()
);

-- 構造化出力でどのカスタムスキーマを使用したかを追跡
alter table public.structured_outputs 
add column if not exists custom_schema_id uuid references public.custom_schemas(id),
add column if not exists schema_version text; -- 使用したスキーマのバージョン情報

-- インデックス作成
create index if not exists idx_custom_schemas_is_default on public.custom_schemas (is_default);
create index if not exists idx_custom_schemas_is_active on public.custom_schemas (is_active);
create index if not exists idx_schema_fields_custom_schema_id on public.schema_fields (custom_schema_id);
create index if not exists idx_schema_fields_group_name on public.schema_fields (group_name);
create index if not exists idx_field_enum_options_schema_field_id on public.field_enum_options (schema_field_id);
create index if not exists idx_structured_outputs_custom_schema_id on public.structured_outputs (custom_schema_id);

-- updated_atの自動更新トリガー
drop trigger if exists trg_updated_at_custom_schemas on public.custom_schemas;
create trigger trg_updated_at_custom_schemas
before update on public.custom_schemas
for each row execute procedure set_updated_at();

drop trigger if exists trg_updated_at_schema_fields on public.schema_fields;
create trigger trg_updated_at_schema_fields
before update on public.schema_fields
for each row execute procedure set_updated_at();

-- デフォルトスキーマの初期データを挿入
-- まずは1つのデフォルトスキーマを作成
insert into public.custom_schemas (name, description, is_default, is_active, base_schema_version, schema_groups)
values (
  'デフォルトスキーマ',
  'システム標準の構造化データ抽出スキーマ（6グループ構成）',
  true,
  true,
  'v1.0',
  '[
    {"name": "転職活動状況・エージェント関連", "description": "転職活動状況・エージェント関連"},
    {"name": "転職理由・希望条件", "description": "転職理由・希望条件"},
    {"name": "職歴・経験", "description": "職歴・経験"},
    {"name": "希望業界・職種", "description": "希望業界・職種"},
    {"name": "年収・待遇条件", "description": "年収・待遇条件"},
    {"name": "企業文化・キャリアビジョン", "description": "企業文化・キャリアビジョン"}
  ]'::jsonb
);

-- デフォルトスキーマのIDを取得するための一時変数的手法
-- 実際のフィールド定義は別途バックエンドから登録する方が管理しやすい