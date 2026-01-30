-- Add Zoho sync status tracking columns to structured_outputs table
-- This allows tracking the sync status and error details for each structured output

ALTER TABLE public.structured_outputs
ADD COLUMN IF NOT EXISTS zoho_sync_status TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS zoho_sync_error TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS zoho_synced_at TIMESTAMPTZ DEFAULT NULL,
ADD COLUMN IF NOT EXISTS zoho_sync_fields_count INTEGER DEFAULT NULL;

-- Add index for efficient filtering by sync status
CREATE INDEX IF NOT EXISTS idx_structured_outputs_zoho_sync_status
  ON public.structured_outputs (zoho_sync_status)
  WHERE zoho_sync_status IS NOT NULL;

-- Comment for documentation
COMMENT ON COLUMN public.structured_outputs.zoho_sync_status IS 'Zoho sync status: success | failed | auth_error | field_mapping_error | error | NULL (not synced)';
COMMENT ON COLUMN public.structured_outputs.zoho_sync_error IS 'Error message when sync fails';
COMMENT ON COLUMN public.structured_outputs.zoho_synced_at IS 'Timestamp of last successful sync';
COMMENT ON COLUMN public.structured_outputs.zoho_sync_fields_count IS 'Number of fields successfully synced to Zoho';
