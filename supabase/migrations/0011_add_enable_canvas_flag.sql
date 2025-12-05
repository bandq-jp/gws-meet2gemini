-- Enable/disable Canvas (SEO article editing) per marketing model asset

alter table if exists public.marketing_model_assets
  add column if not exists enable_canvas boolean not null default true;

-- Backfill existing rows defensively
update public.marketing_model_assets
set enable_canvas = coalesce(enable_canvas, true);
