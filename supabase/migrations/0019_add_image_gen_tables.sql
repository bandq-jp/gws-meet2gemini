-- Image generation platform tables
-- スタイルテンプレート・リファレンス画像・生成セッション管理

-- 1. スタイルテンプレート
CREATE TABLE IF NOT EXISTS public.image_gen_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  category TEXT,
  aspect_ratio TEXT DEFAULT 'auto',
  image_size TEXT DEFAULT '1K' CHECK (image_size IN ('1K', '2K', '4K')),
  system_prompt TEXT,
  thumbnail_url TEXT,
  visibility TEXT DEFAULT 'public' CHECK (visibility IN ('public', 'private')),
  created_by TEXT,
  created_by_email TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_updated_at_image_gen_templates ON public.image_gen_templates;
CREATE TRIGGER trg_updated_at_image_gen_templates
BEFORE UPDATE ON public.image_gen_templates
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

-- 2. リファレンス画像
CREATE TABLE IF NOT EXISTS public.image_gen_references (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id UUID NOT NULL REFERENCES public.image_gen_templates(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  mime_type TEXT,
  size_bytes INTEGER,
  sort_order INTEGER DEFAULT 0,
  label TEXT DEFAULT 'style' CHECK (label IN ('object', 'person', 'style')),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_image_gen_references_template
  ON public.image_gen_references(template_id);

-- 3. 生成セッション
CREATE TABLE IF NOT EXISTS public.image_gen_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id UUID REFERENCES public.image_gen_templates(id) ON DELETE SET NULL,
  title TEXT,
  aspect_ratio TEXT DEFAULT 'auto',
  image_size TEXT DEFAULT '1K' CHECK (image_size IN ('1K', '2K', '4K')),
  created_by TEXT,
  created_by_email TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_updated_at_image_gen_sessions ON public.image_gen_sessions;
CREATE TRIGGER trg_updated_at_image_gen_sessions
BEFORE UPDATE ON public.image_gen_sessions
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

-- 4. 生成メッセージ
CREATE TABLE IF NOT EXISTS public.image_gen_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES public.image_gen_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  text_content TEXT,
  image_url TEXT,
  storage_path TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_image_gen_messages_session
  ON public.image_gen_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_image_gen_messages_session_created
  ON public.image_gen_messages(session_id, created_at);

-- Storage buckets are created via Supabase dashboard or API
-- Bucket names: image-gen-references, image-gen-outputs
