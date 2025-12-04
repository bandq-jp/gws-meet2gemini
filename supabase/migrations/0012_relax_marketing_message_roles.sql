-- Relax role constraint to avoid future ChatKit item type breakage
ALTER TABLE IF EXISTS public.marketing_messages
  DROP CONSTRAINT IF EXISTS marketing_messages_role_check;
-- Optional: keep role NOT NULL but allow any value (ChatKit may introduce new types)
ALTER TABLE IF EXISTS public.marketing_messages
  ALTER COLUMN role SET NOT NULL;
