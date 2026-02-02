-- Add context_items to marketing_conversations for Responses API context persistence
ALTER TABLE marketing_conversations
  ADD COLUMN IF NOT EXISTS context_items JSONB;

-- Add activity_items to marketing_messages for ActivityItem timeline persistence
ALTER TABLE marketing_messages
  ADD COLUMN IF NOT EXISTS activity_items JSONB;
