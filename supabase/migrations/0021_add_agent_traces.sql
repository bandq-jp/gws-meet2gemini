-- =============================================================================
-- Agent Traces & Spans Tables (OTel Span Storage for Agent Analytics)
-- =============================================================================

-- agent_traces: 各会話(invocation)のルートトレース
CREATE TABLE IF NOT EXISTS public.agent_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id TEXT NOT NULL,
    conversation_id TEXT,
    user_email TEXT,
    user_id TEXT,

    root_agent_name TEXT NOT NULL DEFAULT 'BAndQOrchestrator',
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_ms FLOAT,
    status TEXT DEFAULT 'ok',
    error_message TEXT,

    total_llm_calls INT DEFAULT 0,
    total_tool_calls INT DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    sub_agents_used TEXT[] DEFAULT '{}',
    tools_used TEXT[] DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(trace_id)
);

-- agent_spans: 個別スパン (invoke_agent, call_llm, execute_tool, send_data)
CREATE TABLE IF NOT EXISTS public.agent_spans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id TEXT NOT NULL REFERENCES agent_traces(trace_id) ON DELETE CASCADE,
    span_id TEXT NOT NULL,
    parent_span_id TEXT,

    operation_name TEXT NOT NULL,
    agent_name TEXT,
    tool_name TEXT,
    model_name TEXT,

    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_ms FLOAT,

    input_tokens INT,
    output_tokens INT,

    status TEXT DEFAULT 'ok',
    finish_reason TEXT,
    error_message TEXT,

    attributes JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(span_id)
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_agent_traces_user ON agent_traces(user_email);
CREATE INDEX IF NOT EXISTS idx_agent_traces_started ON agent_traces(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_traces_conversation ON agent_traces(conversation_id);
CREATE INDEX IF NOT EXISTS idx_agent_spans_trace ON agent_spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_agent_spans_operation ON agent_spans(operation_name);
CREATE INDEX IF NOT EXISTS idx_agent_spans_agent ON agent_spans(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_spans_tool ON agent_spans(tool_name);
CREATE INDEX IF NOT EXISTS idx_agent_spans_started ON agent_spans(started_at DESC);

-- =============================================================================
-- 集計ビュー
-- =============================================================================

CREATE OR REPLACE VIEW agent_daily_summary AS
SELECT
    DATE(started_at) as day,
    COUNT(*) as trace_count,
    COUNT(DISTINCT user_email) as unique_users,
    AVG(duration_ms) as avg_duration_ms,
    SUM(total_llm_calls) as total_llm_calls,
    SUM(total_tool_calls) as total_tool_calls,
    SUM(total_input_tokens) as total_input_tokens,
    SUM(total_output_tokens) as total_output_tokens,
    COUNT(*) FILTER (WHERE status = 'error') as error_count
FROM agent_traces
GROUP BY DATE(started_at);

CREATE OR REPLACE VIEW agent_tool_summary AS
SELECT
    tool_name,
    agent_name,
    COUNT(*) as call_count,
    AVG(duration_ms) as avg_duration_ms,
    MIN(duration_ms) as min_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    COUNT(*) FILTER (WHERE status = 'error') as error_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'ok') / NULLIF(COUNT(*), 0), 1) as success_rate
FROM agent_spans
WHERE operation_name = 'execute_tool' AND tool_name IS NOT NULL
GROUP BY tool_name, agent_name;
