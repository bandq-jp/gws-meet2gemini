-- Fix image_size CHECK constraint to include '0.5K' which is supported by Gemini API
-- Previously only ('1K', '2K', '4K') were allowed, but the frontend and Gemini API support '0.5K'

-- Drop and recreate CHECK constraint on image_gen_templates
ALTER TABLE image_gen_templates DROP CONSTRAINT IF EXISTS image_gen_templates_image_size_check;
ALTER TABLE image_gen_templates ADD CONSTRAINT image_gen_templates_image_size_check
  CHECK (image_size IN ('0.5K', '1K', '2K', '4K'));

-- Drop and recreate CHECK constraint on image_gen_sessions
ALTER TABLE image_gen_sessions DROP CONSTRAINT IF EXISTS image_gen_sessions_image_size_check;
ALTER TABLE image_gen_sessions ADD CONSTRAINT image_gen_sessions_image_size_check
  CHECK (image_size IN ('0.5K', '1K', '2K', '4K'));
