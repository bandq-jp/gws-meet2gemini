-- =============================================================================
-- Migration: 0022_add_feedback_system.sql
-- Agent Feedback & Annotation System
-- =============================================================================

-- =============================================================================
-- 1. Feedback Dimensions (evaluation criteria master)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.feedback_dimensions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    data_type TEXT NOT NULL DEFAULT 'numeric'
        CHECK (data_type IN ('numeric', 'categorical', 'boolean')),
    min_value FLOAT,
    max_value FLOAT,
    categories TEXT[],
    dimension_group TEXT,
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO feedback_dimensions (key, display_name, description, data_type, min_value, max_value, dimension_group, sort_order) VALUES
    ('accuracy',     '正確性',     '情報の事実的正確さ',         'numeric', 1, 5, 'quality', 1),
    ('relevance',    '関連性',     '質問への回答としての適切さ', 'numeric', 1, 5, 'quality', 2),
    ('completeness', '完全性',     '回答の網羅性',               'numeric', 1, 5, 'quality', 3),
    ('tone',         'トーン',     'ビジネス文脈での適切な口調', 'numeric', 1, 5, 'quality', 4),
    ('tool_usage',   'ツール活用', '適切なツール選択と活用',     'numeric', 1, 5, 'tool_usage', 5),
    ('helpfulness',  '有用性',     '実際の業務に役立つか',       'numeric', 1, 5, 'quality', 6)
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- 2. Feedback Tags (predefined issue/praise labels)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.feedback_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    sentiment TEXT NOT NULL DEFAULT 'negative'
        CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    color TEXT,
    icon TEXT,
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO feedback_tags (key, display_name, sentiment, color, sort_order) VALUES
    ('hallucination',     'ハルシネーション',     'negative', '#ef4444', 1),
    ('wrong_tool',        'ツール選択ミス',       'negative', '#f97316', 2),
    ('incomplete',        '回答不完全',           'negative', '#eab308', 3),
    ('wrong_agent',       'エージェント選択ミス', 'negative', '#f97316', 4),
    ('data_error',        'データ取得エラー',     'negative', '#ef4444', 5),
    ('format_issue',      'フォーマット不適切',   'negative', '#a855f7', 6),
    ('too_verbose',       '冗長すぎる',           'negative', '#6b7280', 7),
    ('too_brief',         '簡潔すぎる',           'negative', '#6b7280', 8),
    ('stale_data',        '古いデータ',           'negative', '#eab308', 9),
    ('wrong_language',    '言語ミス',             'negative', '#ef4444', 10),
    ('great_insight',     '優れた洞察',           'positive', '#22c55e', 11),
    ('good_tool_use',     '適切なツール活用',     'positive', '#22c55e', 12),
    ('comprehensive',     '包括的な回答',         'positive', '#22c55e', 13),
    ('actionable',        '実用的な提案',         'positive', '#22c55e', 14),
    ('needs_review',      '要確認',               'neutral',  '#6b7280', 15),
    ('edge_case',         'エッジケース',         'neutral',  '#6b7280', 16)
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- 3. Message Feedback (per-message rating)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.message_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT NOT NULL REFERENCES marketing_messages(id) ON DELETE CASCADE,
    conversation_id TEXT NOT NULL REFERENCES marketing_conversations(id) ON DELETE CASCADE,
    user_email TEXT NOT NULL,
    user_id TEXT,
    rating TEXT CHECK (rating IN ('good', 'bad')),
    comment TEXT,
    correction TEXT,
    dimension_scores JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT '{}',
    source_type TEXT NOT NULL DEFAULT 'human'
        CHECK (source_type IN ('human', 'auto_eval', 'model')),
    review_status TEXT NOT NULL DEFAULT 'new'
        CHECK (review_status IN ('new', 'reviewed', 'actioned', 'dismissed')),
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    content_hash TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(message_id, user_email)
);

CREATE INDEX idx_feedback_conversation ON message_feedback(conversation_id);
CREATE INDEX idx_feedback_rating ON message_feedback(rating);
CREATE INDEX idx_feedback_review_status ON message_feedback(review_status);
CREATE INDEX idx_feedback_created ON message_feedback(created_at DESC);
CREATE INDEX idx_feedback_tags ON message_feedback USING GIN(tags);

-- =============================================================================
-- 4. Message Annotations (segment-level)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.message_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT NOT NULL REFERENCES marketing_messages(id) ON DELETE CASCADE,
    conversation_id TEXT NOT NULL REFERENCES marketing_conversations(id) ON DELETE CASCADE,
    user_email TEXT NOT NULL,
    user_id TEXT,
    selector JSONB NOT NULL,
    comment TEXT,
    tags TEXT[] DEFAULT '{}',
    severity TEXT DEFAULT 'info'
        CHECK (severity IN ('critical', 'major', 'minor', 'info', 'positive')),
    correction TEXT,
    review_status TEXT NOT NULL DEFAULT 'new'
        CHECK (review_status IN ('new', 'reviewed', 'actioned', 'dismissed')),
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    content_hash TEXT,
    is_stale BOOLEAN DEFAULT FALSE,
    source_type TEXT NOT NULL DEFAULT 'human'
        CHECK (source_type IN ('human', 'auto_eval', 'model')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_annotation_message ON message_annotations(message_id);
CREATE INDEX idx_annotation_conversation ON message_annotations(conversation_id);
CREATE INDEX idx_annotation_severity ON message_annotations(severity);
CREATE INDEX idx_annotation_review ON message_annotations(review_status);
CREATE INDEX idx_annotation_tags ON message_annotations USING GIN(tags);

-- =============================================================================
-- 5. Aggregation Views
-- =============================================================================

CREATE OR REPLACE VIEW feedback_conversation_summary AS
SELECT
    f.conversation_id,
    COUNT(*) AS total_feedback,
    COUNT(*) FILTER (WHERE f.rating = 'good') AS good_count,
    COUNT(*) FILTER (WHERE f.rating = 'bad') AS bad_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE f.rating = 'bad')
        / NULLIF(COUNT(*) FILTER (WHERE f.rating IS NOT NULL), 0), 1
    ) AS negative_pct,
    COUNT(DISTINCT f.user_email) AS unique_raters,
    MAX(f.created_at) AS latest_feedback_at
FROM message_feedback f
GROUP BY f.conversation_id;

CREATE OR REPLACE VIEW feedback_tag_frequency AS
SELECT
    tag,
    COUNT(*) AS occurrence_count,
    COUNT(DISTINCT f.conversation_id) AS affected_conversations,
    COUNT(DISTINCT f.user_email) AS reporters
FROM message_feedback f, unnest(f.tags) AS tag
GROUP BY tag
ORDER BY occurrence_count DESC;

CREATE OR REPLACE VIEW feedback_daily_trend AS
SELECT
    DATE(f.created_at) AS day,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE f.rating = 'good') AS good,
    COUNT(*) FILTER (WHERE f.rating = 'bad') AS bad,
    COUNT(*) FILTER (WHERE f.review_status = 'new') AS unreviewed,
    COUNT(DISTINCT f.message_id) AS messages_rated,
    COUNT(DISTINCT f.conversation_id) AS conversations_touched
FROM message_feedback f
GROUP BY DATE(f.created_at)
ORDER BY day DESC;

-- =============================================================================
-- 6. RLS
-- =============================================================================

ALTER TABLE feedback_dimensions ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_annotations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service role full access feedback_dimensions"
    ON feedback_dimensions FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "service role full access feedback_tags"
    ON feedback_tags FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "service role full access message_feedback"
    ON message_feedback FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "service role full access message_annotations"
    ON message_annotations FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');
