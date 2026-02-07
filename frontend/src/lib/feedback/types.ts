/**
 * Feedback & Annotation System Types
 */

// =============================================================================
// Master Data
// =============================================================================

export interface FeedbackDimension {
  id: string;
  key: string;
  display_name: string;
  description: string | null;
  data_type: "numeric" | "categorical" | "boolean";
  min_value: number | null;
  max_value: number | null;
  categories: string[] | null;
  dimension_group: string | null;
  sort_order: number;
}

export interface FeedbackTag {
  id: string;
  key: string;
  display_name: string;
  description: string | null;
  sentiment: "positive" | "negative" | "neutral";
  color: string | null;
  icon: string | null;
  sort_order: number;
}

// =============================================================================
// Feedback (message-level)
// =============================================================================

export type Rating = "good" | "bad";
export type ReviewStatus = "new" | "reviewed" | "actioned" | "dismissed";

export interface MessageFeedback {
  id: string;
  message_id: string;
  conversation_id: string;
  user_email: string;
  user_id: string | null;
  rating: Rating | null;
  comment: string | null;
  correction: string | null;
  dimension_scores: Record<string, number>;
  tags: string[];
  source_type: "human" | "auto_eval" | "model";
  review_status: ReviewStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  content_hash: string | null;
  trace_id: string | null;
  created_at: string;
  updated_at: string;
  // Joined data from list endpoint
  marketing_messages?: {
    plain_text: string | null;
    role: string;
    created_at: string;
  };
  marketing_conversations?: {
    title: string;
  };
}

export interface FeedbackCreatePayload {
  rating?: Rating | null;
  comment?: string | null;
  correction?: string | null;
  dimension_scores?: Record<string, number> | null;
  tags?: string[] | null;
}

// =============================================================================
// Annotations (segment-level)
// =============================================================================

export type AnnotationSeverity = "critical" | "major" | "minor" | "info" | "positive";

export interface TextSpanSelector {
  type: "text_span";
  position: { start: number; end: number };
  quote: { prefix: string; exact: string; suffix: string };
}

export interface ActivityItemSelector {
  type: "activity_item";
  activity_item_kind: string;
  tool_name?: string;
  call_id?: string;
  agent_name?: string;
}

export interface FullMessageSelector {
  type: "full_message";
}

export type AnnotationSelector = TextSpanSelector | ActivityItemSelector | FullMessageSelector;

export interface MessageAnnotation {
  id: string;
  message_id: string;
  conversation_id: string;
  user_email: string;
  selector: AnnotationSelector;
  comment: string | null;
  tags: string[];
  severity: AnnotationSeverity;
  correction: string | null;
  review_status: ReviewStatus;
  reviewed_by: string | null;
  review_notes: string | null;
  content_hash: string | null;
  is_stale: boolean;
  created_at: string;
  updated_at: string;
}

export interface AnnotationCreatePayload {
  message_id: string;
  conversation_id: string;
  selector: AnnotationSelector;
  comment?: string | null;
  tags?: string[] | null;
  severity?: AnnotationSeverity;
  correction?: string | null;
  content_hash?: string | null;
}

// =============================================================================
// Dashboard
// =============================================================================

export interface FeedbackOverview {
  total: number;
  good: number;
  bad: number;
  unreviewed: number;
  good_pct: number;
  bad_pct: number;
  top_tags: Array<{ tag: string; count: number }>;
  trend: Array<{ day: string; good: number; bad: number; total: number }>;
}

export interface FeedbackListResponse {
  items: MessageFeedback[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// =============================================================================
// UI State
// =============================================================================

export interface FeedbackState {
  /** Map of message_id -> user's feedback for that message */
  feedbackByMessage: Record<string, MessageFeedback>;
  /** Map of message_id -> annotations for that message */
  annotationsByMessage: Record<string, MessageAnnotation[]>;
  /** Whether the user is in FB mode */
  isFeedbackMode: boolean;
}
