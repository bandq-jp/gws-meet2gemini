// --- Activity Timeline (unified reasoning + tool call ordering) ---

export interface ReasoningActivityItem {
  id: string;
  kind: "reasoning";
  sequence: number;
  content: string;
}

export interface ToolActivityItem {
  id: string;
  kind: "tool";
  sequence: number;
  name: string;
  call_id?: string;
  arguments?: string;
  output?: string; // undefined = executing, string = completed
}

export interface AskUserQuestionItem {
  id: string;
  question: string;
  type: "choice" | "text" | "confirm";
  options: string[];
}

export interface AskUserActivityItem {
  id: string;
  kind: "ask_user";
  sequence: number;
  groupId: string;
  questions: AskUserQuestionItem[];
  responses?: Record<string, string>;
}

export interface TextActivityItem {
  id: string;
  kind: "text";
  sequence: number;
  content: string;
}

export type ActivityItem =
  | ReasoningActivityItem
  | ToolActivityItem
  | AskUserActivityItem
  | TextActivityItem;

// --- Message ---

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  activityItems?: ActivityItem[];
  isStreaming?: boolean;
}

// --- Conversation / Thread ---

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
  is_shared?: boolean;
}

// --- SSE Stream Events ---

export interface StreamEvent {
  type:
    | "text_delta"
    | "tool_call"
    | "tool_result"
    | "reasoning"
    | "ask_user"
    | "done"
    | "error"
    | "response_created"
    | "keepalive";
  content?: string;
  call_id?: string;
  name?: string;
  arguments?: string;
  output?: string;
  message?: string;
  text?: string;
  conversation_id?: string;
  has_summary?: boolean;
  // ask_user
  group_id?: string;
  questions?: AskUserQuestionItem[];
}

export interface PendingQuestionGroup {
  groupId: string;
  questions: AskUserQuestionItem[];
}

// --- Model Asset ---

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
  enable_canvas?: boolean;
  enable_zoho_crm?: boolean;
  system_prompt_addition?: string | null;
  visibility?: "public" | "private";
  created_by?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
}

// --- Share ---

export interface ShareInfo {
  thread_id: string;
  is_shared: boolean;
  share_url?: string | null;
  owner_email?: string;
  is_owner: boolean;
  can_toggle?: boolean;
  shared_at?: string | null;
}

// --- DB message record (for loading from API) ---

export interface MessageRecord {
  id: string;
  role: string;
  content: string;
  message_type?: string;
  activity_items?: ActivityItemRecord[] | null;
  created_at: string;
}

export interface ActivityItemRecord {
  kind: string;
  sequence: number;
  content?: string;
  name?: string;
  call_id?: string;
  arguments?: string;
  output?: string;
  groupId?: string;
  questions?: AskUserQuestionItem[];
  responses?: Record<string, string>;
}
