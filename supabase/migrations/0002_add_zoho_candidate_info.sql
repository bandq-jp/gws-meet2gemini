-- Add Zoho CRM candidate information to structured_outputs table
alter table public.structured_outputs 
add column if not exists zoho_candidate_id text,
add column if not exists zoho_record_id text,
add column if not exists zoho_candidate_name text,
add column if not exists zoho_candidate_email text;

-- Add index for faster lookups by candidate
create index if not exists idx_structured_outputs_zoho_candidate_id
  on public.structured_outputs (zoho_candidate_id);

-- Add index for record lookups
create index if not exists idx_structured_outputs_zoho_record_id
  on public.structured_outputs (zoho_record_id);