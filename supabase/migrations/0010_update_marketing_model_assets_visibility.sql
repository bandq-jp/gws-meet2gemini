-- Align verbosity values with ChatKit (low/medium/high) and add visibility/creator metadata

alter table if exists public.marketing_model_assets
  drop constraint if exists marketing_model_assets_verbosity_check;

alter table if exists public.marketing_model_assets
  add column if not exists visibility text not null default 'public' check (visibility in ('public','private')),
  add column if not exists created_by_email text,
  add column if not exists created_by_name text;

-- Backfill existing data **before** re-adding constraint
update public.marketing_model_assets
set visibility = coalesce(visibility, 'public'),
    verbosity = case
      when verbosity = 'short' then 'low'
      when verbosity = 'long' then 'high'
      else verbosity
    end;

alter table if exists public.marketing_model_assets
  add constraint marketing_model_assets_verbosity_check
  check (verbosity in ('low','medium','high'));
