ALTER TABLE public.marketing_model_assets
  DROP CONSTRAINT IF EXISTS marketing_model_assets_reasoning_effort_check;

ALTER TABLE public.marketing_model_assets
  ADD CONSTRAINT marketing_model_assets_reasoning_effort_check
  CHECK (reasoning_effort in ('low', 'medium', 'high', 'xhigh'));
