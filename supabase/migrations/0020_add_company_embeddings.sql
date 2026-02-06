-- Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- Company Chunks Table (Semantic Search)
-- =============================================================================
-- Stores vectorized chunks of company data for semantic search
-- Each company has multiple chunks (overview, requirements, salary, growth, wlb, culture)

CREATE TABLE IF NOT EXISTS public.company_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company identification
    company_name TEXT NOT NULL,

    -- Chunk information
    chunk_type TEXT NOT NULL,  -- 'overview', 'requirements', 'salary', 'growth', 'wlb', 'culture'
    chunk_text TEXT NOT NULL,  -- The text that was embedded

    -- Vector embedding (768 dimensions for Gemini embedding-001)
    embedding vector(768) NOT NULL,

    -- Metadata for filtering (JSON for flexibility)
    metadata JSONB NOT NULL DEFAULT '{}',
    -- Expected metadata structure:
    -- {
    --   "age_limit": 35,
    --   "max_salary": 1000,
    --   "locations": ["東京都", "大阪府"],
    --   "remote": "週2-3",
    --   "recommendation": "紹介推奨",
    --   "layer": "ミドル",
    --   "has_hr_job": true,
    --   "has_referral_job": true
    -- }

    -- Source tracking
    source_sheet TEXT DEFAULT 'DB',
    source_row_id TEXT,

    -- Versioning
    vectorized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash TEXT,  -- For change detection

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint per company per chunk type
    UNIQUE(company_name, chunk_type)
);

-- Index for vector similarity search (IVFFlat for approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_company_chunks_embedding
ON public.company_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for metadata filtering
CREATE INDEX IF NOT EXISTS idx_company_chunks_metadata
ON public.company_chunks
USING gin (metadata);

-- Index for company name lookups
CREATE INDEX IF NOT EXISTS idx_company_chunks_company_name
ON public.company_chunks (company_name);

-- Index for chunk type filtering
CREATE INDEX IF NOT EXISTS idx_company_chunks_chunk_type
ON public.company_chunks (chunk_type);

-- =============================================================================
-- PIC Recommendations Table
-- =============================================================================
-- Stores per-advisor recommended companies from X sheets

CREATE TABLE IF NOT EXISTS public.pic_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pic_name TEXT NOT NULL,           -- Advisor name (成田, 小野寺, etc.)
    company_name TEXT NOT NULL,
    recommendation_notes TEXT,        -- Notes about why this company is recommended
    priority_rank INT,                -- Priority ranking (lower = higher priority)

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(pic_name, company_name)
);

-- Index for PIC lookups
CREATE INDEX IF NOT EXISTS idx_pic_recommendations_pic_name
ON public.pic_recommendations (pic_name);

-- =============================================================================
-- Semantic Search Function
-- =============================================================================
-- Similar to search_memories_by_embedding but for company chunks

CREATE OR REPLACE FUNCTION search_company_chunks(
    query_embedding vector(768),
    match_chunk_types TEXT[] DEFAULT NULL,  -- Filter by chunk types (NULL = all)
    filter_max_age INT DEFAULT NULL,        -- Filter by age limit
    filter_min_salary INT DEFAULT NULL,     -- Filter by minimum salary
    filter_locations TEXT[] DEFAULT NULL,   -- Filter by locations (any match)
    filter_remote TEXT DEFAULT NULL,        -- Filter by remote option
    match_count INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    company_name TEXT,
    chunk_type TEXT,
    chunk_text TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cc.id,
        cc.company_name,
        cc.chunk_type,
        cc.chunk_text,
        cc.metadata,
        1 - (cc.embedding <=> query_embedding) AS similarity
    FROM public.company_chunks cc
    WHERE
        -- Chunk type filter
        (match_chunk_types IS NULL OR cc.chunk_type = ANY(match_chunk_types))
        -- Age filter (candidate age <= company age limit)
        AND (filter_max_age IS NULL OR (cc.metadata->>'age_limit')::INT >= filter_max_age OR cc.metadata->>'age_limit' IS NULL)
        -- Salary filter (company max salary >= candidate desired salary)
        AND (filter_min_salary IS NULL OR (cc.metadata->>'max_salary')::INT >= filter_min_salary OR cc.metadata->>'max_salary' IS NULL)
        -- Location filter (any location matches)
        AND (filter_locations IS NULL OR cc.metadata->'locations' ?| filter_locations)
        -- Remote filter
        AND (filter_remote IS NULL OR cc.metadata->>'remote' ILIKE '%' || filter_remote || '%')
        -- Similarity threshold
        AND (1 - (cc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY cc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- =============================================================================
-- Triggers for updated_at
-- =============================================================================

DROP TRIGGER IF EXISTS trg_updated_at_company_chunks ON public.company_chunks;
CREATE TRIGGER trg_updated_at_company_chunks
BEFORE UPDATE ON public.company_chunks
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

DROP TRIGGER IF EXISTS trg_updated_at_pic_recommendations ON public.pic_recommendations;
CREATE TRIGGER trg_updated_at_pic_recommendations
BEFORE UPDATE ON public.pic_recommendations
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE public.company_chunks IS 'Vectorized company data chunks for semantic search. Data from Google Sheets company database.';
COMMENT ON TABLE public.pic_recommendations IS 'Per-advisor recommended companies from X sheets in the company database.';
COMMENT ON FUNCTION search_company_chunks IS 'Semantic search for company chunks using pgvector cosine similarity with optional metadata filters.';
