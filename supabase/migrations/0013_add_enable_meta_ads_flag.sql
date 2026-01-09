-- Enable/disable Meta Ads MCP per marketing model asset

alter table if exists public.marketing_model_assets
  add column if not exists enable_meta_ads boolean not null default true;

-- Backfill existing rows defensively
update public.marketing_model_assets
set enable_meta_ads = coalesce(enable_meta_ads, true);
