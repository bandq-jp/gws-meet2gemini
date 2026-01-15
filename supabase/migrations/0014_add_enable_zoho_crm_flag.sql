-- Enable/disable Zoho CRM tools per marketing model asset

alter table if exists public.marketing_model_assets
  add column if not exists enable_zoho_crm boolean not null default true;

-- Backfill existing rows defensively
update public.marketing_model_assets
set enable_zoho_crm = coalesce(enable_zoho_crm, true);

comment on column public.marketing_model_assets.enable_zoho_crm is 'Enable Zoho CRM job seeker search and aggregation tools for this asset';
