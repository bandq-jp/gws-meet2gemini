-- Add GPT-5.4 and GPT-5.4-mini as selectable models
-- The base_model column already exists (text, no CHECK constraint), so just update defaults and standard preset

-- Update the default for new rows
ALTER TABLE public.marketing_model_assets
  ALTER COLUMN base_model SET DEFAULT 'gpt-5.4';

-- Update the standard preset to use GPT-5.4
UPDATE public.marketing_model_assets
SET
  base_model = 'gpt-5.4',
  description = '既定のマーケティングエージェント設定（GPT-5.4、高推論、Web検索+コード+各MCP有効）'
WHERE id = 'standard';
