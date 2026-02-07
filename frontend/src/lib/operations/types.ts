// Agent Analytics types

export type PeriodFilter = "today" | "7d" | "30d" | "all";

export interface AnalyticsOverview {
  total_conversations: number;
  total_tool_calls: number;
  total_llm_calls: number;
  error_rate: number;
  error_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  unique_users: number;
  avg_duration_ms: number;
}

export interface TraceOverview {
  id: string;
  trace_id: string;
  conversation_id: string | null;
  user_email: string | null;
  root_agent_name: string;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  status: "ok" | "error";
  error_message: string | null;
  total_llm_calls: number;
  total_tool_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  sub_agents_used: string[];
  tools_used: string[];
}

export interface SpanDetail {
  id: string;
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  operation_name: string;
  agent_name: string | null;
  tool_name: string | null;
  model_name: string | null;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  status: string;
  finish_reason: string | null;
  error_message: string | null;
  attributes: Record<string, unknown>;
  children?: SpanDetail[];
}

export interface TraceDetailResponse {
  trace: TraceOverview;
  spans: SpanDetail[];
  tree: SpanDetail[];
}

export interface ToolUsageStat {
  tool_name: string;
  agent_name: string | null;
  call_count: number;
  avg_duration_ms: number;
  success_rate: number;
  error_count: number;
}

export interface AgentRoutingStat {
  agent_name: string;
  call_count: number;
  avg_tools_per_call: number;
}

export interface TokenUsageDaily {
  day: string;
  input_tokens: number;
  output_tokens: number;
  trace_count: number;
  estimated_cost_usd: number;
}

export interface UserUsageStat {
  user_email: string;
  trace_count: number;
  last_used: string;
  total_tokens: number;
}

export interface AgentError {
  trace_id: string;
  span_id: string;
  agent_name: string | null;
  tool_name: string | null;
  error_message: string | null;
  started_at: string;
  operation_name: string;
}
