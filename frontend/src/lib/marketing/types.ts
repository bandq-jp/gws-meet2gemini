/**
 * Marketing AI Chat Types
 *
 * Type definitions for the native OpenAI Agents SDK streaming interface.
 * Replaces ChatKit types with custom SSE event handling.
 */

// =============================================================================
// SSE Stream Event Types
// =============================================================================

export type StreamEventType =
  | "text_delta"
  | "response_created"
  | "tool_call"
  | "tool_result"
  | "reasoning"
  | "sub_agent_event"
  | "agent_updated"
  | "ask_user"
  | "chart"
  | "progress"
  | "done"
  | "error"
  | "_context_items";

export interface BaseStreamEvent {
  type: StreamEventType;
}

export interface TextDeltaEvent extends BaseStreamEvent {
  type: "text_delta";
  content: string;
}

export interface ResponseCreatedEvent extends BaseStreamEvent {
  type: "response_created";
}

export interface ToolCallEvent extends BaseStreamEvent {
  type: "tool_call";
  call_id: string;
  name: string;
  arguments?: string;
}

export interface ToolResultEvent extends BaseStreamEvent {
  type: "tool_result";
  call_id: string;
  output: string;
}

export interface ReasoningEvent extends BaseStreamEvent {
  type: "reasoning";
  content: string;
  has_summary?: boolean;
}

export interface SubAgentEventData {
  tool_name?: string;
  call_id?: string;
  output_preview?: string;
  content?: string;
  arguments?: string;
  error?: string;
}

export interface SubAgentEvent extends BaseStreamEvent {
  type: "sub_agent_event";
  agent: string;
  event_type: "started" | "tool_called" | "tool_output" | "reasoning" | "text_delta" | "message_output" | "tool_error";
  data?: SubAgentEventData;
}

export interface AgentUpdatedEvent extends BaseStreamEvent {
  type: "agent_updated";
  agent: string;
}

export interface AskUserQuestionItem {
  question: string;
  header: string;
  options: Array<{ label: string; description: string }>;
  multiSelect?: boolean;
}

export interface AskUserEvent extends BaseStreamEvent {
  type: "ask_user";
  group_id: string;
  questions: AskUserQuestionItem[];
}

// Chart Y-axis key configuration
export interface ChartYKey {
  key: string;
  label: string;
  color?: string;
}

// Chart table column configuration
export interface ChartColumn {
  key: string;
  label: string;
  align?: "left" | "right" | "center";
}

// Chart specification for render_chart function tool
export interface ChartSpec {
  type:
    | "line"
    | "bar"
    | "area"
    | "pie"
    | "donut"
    | "scatter"
    | "radar"
    | "funnel"
    | "table";
  title?: string;
  description?: string;
  data: Record<string, unknown>[];
  // line/bar/area/scatter
  xKey?: string;
  yKeys?: ChartYKey[];
  // pie/donut
  nameKey?: string;
  valueKey?: string;
  // table
  columns?: ChartColumn[];
  // radar
  categories?: string[];
  // funnel
  nameField?: string;
  valueField?: string;
}

export interface ChartEvent extends BaseStreamEvent {
  type: "chart";
  spec: ChartSpec;
}

export interface ProgressEvent extends BaseStreamEvent {
  type: "progress";
  text: string;
}

export interface DoneEvent extends BaseStreamEvent {
  type: "done";
  conversation_id: string;
}

export interface ErrorEvent extends BaseStreamEvent {
  type: "error";
  message: string;
}

export interface ContextItemsEvent extends BaseStreamEvent {
  type: "_context_items";
  items: Array<Record<string, unknown>>;
}

export type StreamEvent =
  | TextDeltaEvent
  | ResponseCreatedEvent
  | ToolCallEvent
  | ToolResultEvent
  | ReasoningEvent
  | SubAgentEvent
  | AgentUpdatedEvent
  | AskUserEvent
  | ChartEvent
  | ProgressEvent
  | DoneEvent
  | ErrorEvent
  | ContextItemsEvent;

// =============================================================================
// Activity Item Types (UI Rendering)
// =============================================================================

export type ActivityItemKind =
  | "text"
  | "tool"
  | "reasoning"
  | "sub_agent"
  | "ask_user"
  | "chart";

export interface BaseActivityItem {
  id: string;
  kind: ActivityItemKind;
  sequence: number;
}

export interface TextActivityItem extends BaseActivityItem {
  kind: "text";
  content: string;
}

export interface ToolActivityItem extends BaseActivityItem {
  kind: "tool";
  name: string;
  callId: string;
  arguments?: string;
  output?: string; // undefined = running, string = complete
}

export interface ReasoningActivityItem extends BaseActivityItem {
  kind: "reasoning";
  content: string;
}

export interface SubAgentActivityItem extends BaseActivityItem {
  kind: "sub_agent";
  agent: string;
  eventType: string;
  data?: SubAgentEventData;
  isRunning: boolean;
  // Internal tracking for rich UI
  toolCalls?: Array<{
    callId: string;
    toolName: string;
    isComplete: boolean;
    error?: string;
  }>;
  reasoningContent?: string;
  outputPreview?: string;
}

export interface AskUserActivityItem extends BaseActivityItem {
  kind: "ask_user";
  groupId: string;
  questions: AskUserQuestionItem[];
  answered?: boolean;
}

export interface ChartActivityItem extends BaseActivityItem {
  kind: "chart";
  spec: ChartSpec;
}

export type ActivityItem =
  | TextActivityItem
  | ToolActivityItem
  | ReasoningActivityItem
  | SubAgentActivityItem
  | AskUserActivityItem
  | ChartActivityItem;

// =============================================================================
// Message Types
// =============================================================================

export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  activityItems: ActivityItem[];
  isStreaming: boolean;
  createdAt: Date;
}

// =============================================================================
// Chat State Types
// =============================================================================

export interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
  conversationId: string | null;
  contextItems: Array<Record<string, unknown>> | null;
}

// =============================================================================
// API Request/Response Types
// =============================================================================

export interface ChatStreamRequest {
  message: string;
  conversation_id?: string | null;
  context_items?: Array<Record<string, unknown>> | null;
  model_asset_id?: string | null;
}

export interface ModelAsset {
  id: string;
  name: string;
  description?: string;
  base_model?: string;
  reasoning_effort?: "low" | "medium" | "high" | "xhigh";
  verbosity?: "low" | "medium" | "high";
  enable_web_search?: boolean;
  enable_code_interpreter?: boolean;
  enable_ga4?: boolean;
  enable_meta_ads?: boolean;
  enable_gsc?: boolean;
  enable_ahrefs?: boolean;
  enable_wordpress?: boolean;
  enable_zoho_crm?: boolean;
  system_prompt_addition?: string | null;
  visibility?: "public" | "private";
  created_by?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
}
