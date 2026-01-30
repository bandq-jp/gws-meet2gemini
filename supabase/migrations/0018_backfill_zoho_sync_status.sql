-- Backfill: zoho_record_id が設定済みの既存レコードを同期成功扱いにする
UPDATE public.structured_outputs
SET zoho_sync_status = 'success',
    zoho_synced_at = updated_at
WHERE zoho_record_id IS NOT NULL
  AND zoho_sync_status IS NULL;
