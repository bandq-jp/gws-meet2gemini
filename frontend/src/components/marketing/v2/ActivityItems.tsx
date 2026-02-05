"use client";

/**
 * Activity Items Component
 *
 * Renders activity items (text, tools, reasoning, sub-agents) in sequence.
 */

import type {
  ActivityItem,
  TextActivityItem,
  ToolActivityItem,
  ReasoningActivityItem,
  SubAgentActivityItem,
} from "@/lib/marketing/types";
import { ToolBadge } from "./ToolBadge";
import { ReasoningLine } from "./ReasoningLine";
import { SubAgentEvent } from "./SubAgentEvent";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export interface ActivityItemsProps {
  items: ActivityItem[];
  isStreaming: boolean;
}

export function ActivityItems({ items, isStreaming }: ActivityItemsProps) {
  // Sort items by sequence
  const sortedItems = [...items].sort((a, b) => a.sequence - b.sequence);

  return (
    <div className="space-y-2">
      {sortedItems.map((item) => (
        <ActivityItemRenderer
          key={item.id}
          item={item}
          isStreaming={isStreaming}
        />
      ))}
    </div>
  );
}

interface ActivityItemRendererProps {
  item: ActivityItem;
  isStreaming: boolean;
}

function ActivityItemRenderer({ item, isStreaming }: ActivityItemRendererProps) {
  switch (item.kind) {
    case "text":
      return <TextSegment item={item as TextActivityItem} />;
    case "tool":
      return <ToolBadge item={item as ToolActivityItem} />;
    case "reasoning":
      return <ReasoningLine item={item as ReasoningActivityItem} />;
    case "sub_agent":
      return <SubAgentEvent item={item as SubAgentActivityItem} />;
    case "ask_user":
      // TODO: Implement ask_user UI
      return null;
    case "chart":
      // TODO: Implement chart rendering
      return null;
    default:
      return null;
  }
}

interface TextSegmentProps {
  item: TextActivityItem;
}

function TextSegment({ item }: TextSegmentProps) {
  if (!item.content) return null;

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {item.content}
      </ReactMarkdown>
    </div>
  );
}
