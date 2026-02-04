"use client";

/**
 * ChatMessage Component
 *
 * Renders individual chat messages with full activity timeline support.
 * Based on ga4-oauth-aiagent reference implementation.
 */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import type { Components } from "react-markdown";
import { useState } from "react";
import {
  Wrench,
  Loader2,
  BarChart3,
  Search,
  Database,
  ChevronRight,
  Globe,
  FileText,
  Users,
  TrendingUp,
  Megaphone,
  Bot,
  Brain,
  ExternalLink,
  Code2,
} from "lucide-react";
import { ThinkingIndicator } from "./ThinkingIndicator";
import type {
  Message,
  ActivityItem,
  TextActivityItem,
  ToolActivityItem,
  ReasoningActivityItem,
  SubAgentActivityItem,
} from "@/lib/marketing/types";

// ---------------------------------------------------------------------------
// Sub-agent color mapping
// ---------------------------------------------------------------------------

const SUB_AGENT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  analytics: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  seo: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  meta_ads: { bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
  zoho: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  candidate: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  wordpress: { bg: "bg-cyan-50", text: "text-cyan-700", border: "border-cyan-200" },
  default: { bg: "bg-slate-50", text: "text-slate-700", border: "border-slate-200" },
};

const SUB_AGENT_ICONS: Record<string, typeof Bot> = {
  analytics: BarChart3,
  seo: TrendingUp,
  meta_ads: Megaphone,
  zoho: Users,
  candidate: Users,
  wordpress: FileText,
  default: Bot,
};

const SUB_AGENT_LABELS: Record<string, string> = {
  analytics: "Analytics",
  seo: "SEO",
  meta_ads: "Meta Ads",
  zoho: "Zoho CRM",
  candidate: "Candidate",
  wordpress: "WordPress",
};

// ---------------------------------------------------------------------------
// Tool metadata maps
// ---------------------------------------------------------------------------

const TOOL_ICONS: Record<string, typeof Wrench> = {
  // GA4
  run_report: BarChart3,
  run_realtime_report: BarChart3,
  // GSC
  get_search_analytics: Search,
  get_performance_overview: Search,
  get_advanced_search_analytics: Search,
  list_properties: Database,
  // Zoho
  search_job_seekers: Users,
  get_job_seeker_detail: Users,
  aggregate_by_channel: BarChart3,
  count_job_seekers_by_status: BarChart3,
  get_channel_definitions: Database,
  // Ahrefs
  "site-explorer-organic-keywords": Search,
  "site-explorer-backlinks": ExternalLink,
  "site-explorer-top-pages": TrendingUp,
  // Meta Ads
  get_campaigns: Megaphone,
  get_adsets: Megaphone,
  get_ads: Megaphone,
  // WordPress
  list_posts: FileText,
  create_post: FileText,
  update_post: FileText,
  // Code
  code_interpreter: Code2,
  // Web
  web_search: Globe,
};

const TOOL_LABELS: Record<string, string> = {
  // GA4
  run_report: "レポート取得",
  run_realtime_report: "リアルタイム取得",
  // GSC
  get_search_analytics: "検索分析",
  get_performance_overview: "パフォーマンス概要",
  get_advanced_search_analytics: "詳細検索分析",
  list_properties: "プロパティ一覧",
  // Zoho
  search_job_seekers: "求職者検索",
  get_job_seeker_detail: "求職者詳細",
  aggregate_by_channel: "チャネル集計",
  count_job_seekers_by_status: "ステータス集計",
  get_channel_definitions: "チャネル定義",
  // Meta Ads
  get_campaigns: "キャンペーン取得",
  get_adsets: "広告セット取得",
  get_ads: "広告取得",
  // WordPress
  list_posts: "記事一覧",
  create_post: "記事作成",
  update_post: "記事更新",
  // Code
  code_interpreter: "コード実行",
  // Web
  web_search: "Web検索",
};

// ---------------------------------------------------------------------------
// Markdown components
// ---------------------------------------------------------------------------

const markdownComponents: Components = {
  h1: ({ children }) => (
    <h1 className="text-lg sm:text-xl font-bold text-[#1a1a2e] mt-6 sm:mt-8 mb-2 sm:mb-3 pb-2 border-b-2 border-[#e94560]/20 first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-sm sm:text-base font-bold text-[#1a1a2e] mt-5 sm:mt-6 mb-2 sm:mb-2.5 flex items-center gap-2 first:mt-0">
      <span className="w-1 h-4 sm:h-5 bg-[#e94560] rounded-full inline-block shrink-0" />
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-[13px] sm:text-sm font-bold text-[#374151] mt-3 sm:mt-4 mb-1.5 sm:mb-2 first:mt-0">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="text-[13px] sm:text-sm text-[#374151] leading-[1.8] mb-2.5 sm:mb-3 last:mb-0 break-words">
      {children}
    </p>
  ),
  strong: ({ children }) => (
    <strong className="font-bold text-[#1a1a2e]">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="text-[#6b7280] not-italic text-[11px] sm:text-xs">{children}</em>
  ),
  ul: ({ children }) => (
    <ul className="space-y-1 mb-2.5 sm:mb-3 pl-0 list-none">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="space-y-1 mb-2.5 sm:mb-3 pl-0 list-none counter-reset-item">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="text-[13px] sm:text-sm text-[#374151] leading-relaxed flex items-start gap-1.5 sm:gap-2">
      <span className="text-[#e94560] mt-1.5 shrink-0 text-[8px]">&#9679;</span>
      <span className="min-w-0 break-words">{children}</span>
    </li>
  ),
  table: ({ children }) => (
    <div className="my-3 sm:my-4 rounded-lg border border-[#e5e7eb] overflow-hidden shadow-sm">
      <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: "touch" }}>
        <table className="min-w-full text-xs sm:text-sm">{children}</table>
      </div>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-[#f8f9fb]">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="px-2 sm:px-3.5 py-2 sm:py-2.5 text-left text-[11px] sm:text-xs font-bold text-[#1a1a2e] uppercase tracking-wider border-b border-[#e5e7eb] whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-2 sm:px-3.5 py-2 sm:py-2.5 text-xs sm:text-sm text-[#374151] border-b border-[#f0f1f5] tabular-nums whitespace-nowrap">
      {children}
    </td>
  ),
  tr: ({ children }) => (
    <tr className="hover:bg-[#f8f9fb]/60 transition-colors">
      {children}
    </tr>
  ),
  code: ({ children, className }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <div className="my-2.5 sm:my-3 rounded-lg bg-[#1a1a2e] overflow-hidden">
          <div className="px-3 sm:px-4 py-1.5 bg-[#2a2a4e] text-[10px] text-[#9ca3af] uppercase tracking-wider font-medium">
            {className?.replace("language-", "") || "code"}
          </div>
          <pre className="px-3 sm:px-4 py-2.5 sm:py-3 overflow-x-auto text-[11px] sm:text-xs leading-relaxed">
            <code className="text-[#e5e7eb]">{children}</code>
          </pre>
        </div>
      );
    }
    return (
      <code className="text-[#e94560] bg-[#fef2f2] px-1 sm:px-1.5 py-0.5 rounded text-[11px] sm:text-xs font-medium break-all">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <>{children}</>,
  blockquote: ({ children }) => (
    <blockquote className="my-2.5 sm:my-3 pl-3 sm:pl-4 border-l-[3px] border-[#e94560]/30 text-[#6b7280]">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 sm:my-5 border-t border-[#e5e7eb]" />,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[#3b82f6] underline underline-offset-2 hover:text-[#2563eb] transition-colors break-all"
    >
      {children}
    </a>
  ),
};

// ---------------------------------------------------------------------------
// Helper: grouping for interleaved timeline
// ---------------------------------------------------------------------------

interface TimelineSection {
  type: "activity" | "content";
  items: ActivityItem[];
}

function groupIntoSections(items: ActivityItem[]): TimelineSection[] {
  const sections: TimelineSection[] = [];
  for (const item of items) {
    const isActivity = item.kind === "reasoning" || item.kind === "tool" || item.kind === "sub_agent";
    const sectionType = isActivity ? "activity" : "content";
    const last = sections[sections.length - 1];
    if (last && last.type === sectionType) {
      last.items.push(item);
    } else {
      sections.push({ type: sectionType, items: [item] });
    }
  }
  return sections;
}

interface ItemGroup {
  kind: ActivityItem["kind"];
  items: ActivityItem[];
}

function groupConsecutive(items: ActivityItem[]): ItemGroup[] {
  const groups: ItemGroup[] = [];
  for (const item of items) {
    const last = groups[groups.length - 1];
    if (last && last.kind === item.kind) {
      last.items.push(item);
    } else {
      groups.push({ kind: item.kind, items: [item] });
    }
  }
  return groups;
}

// ---------------------------------------------------------------------------
// ToolBadge
// ---------------------------------------------------------------------------

function ToolBadge({ item }: { item: ToolActivityItem }) {
  const Icon = TOOL_ICONS[item.name] || Wrench;
  const label = TOOL_LABELS[item.name] || item.name;
  const isDone = item.isComplete;

  return (
    <div
      className={`
        inline-flex items-center gap-1 sm:gap-1.5 rounded-md px-2 sm:px-2.5 py-0.5 sm:py-1 text-[11px] sm:text-xs
        transition-all duration-300
        ${isDone
          ? "bg-[#ecfdf5] text-[#065f46] border border-[#a7f3d0]"
          : "bg-[#f0f1f5] text-[#6b7280] border border-[#e5e7eb]"
        }
      `}
    >
      <Icon className="w-3 h-3 shrink-0" />
      <span className="font-medium">{label}</span>
      {isDone ? (
        <span className="text-[#10b981] font-semibold">&#10003;</span>
      ) : (
        <Loader2 className="w-3 h-3 animate-spin" />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SubAgentBadge
// ---------------------------------------------------------------------------

function SubAgentBadge({ item }: { item: SubAgentActivityItem }) {
  const agentKey = item.agent.toLowerCase().replace(/[^a-z]/g, "_");
  const colors = SUB_AGENT_COLORS[agentKey] || SUB_AGENT_COLORS.default;
  const Icon = SUB_AGENT_ICONS[agentKey] || SUB_AGENT_ICONS.default;
  const label = SUB_AGENT_LABELS[agentKey] || item.agent;

  const eventLabel = getEventLabel(item.eventType);

  return (
    <div
      className={`
        inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] sm:text-xs
        transition-all duration-300 border
        ${colors.bg} ${colors.text} ${colors.border}
      `}
    >
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span className="font-semibold">{label}</span>
      <span className="opacity-70">{eventLabel}</span>
      {item.isRunning ? (
        <Loader2 className="w-3 h-3 animate-spin ml-0.5" />
      ) : (
        <span className="text-[#10b981] font-semibold ml-0.5">&#10003;</span>
      )}
    </div>
  );
}

function getEventLabel(eventType: string): string {
  switch (eventType) {
    case "tool_called": return "ツール実行中";
    case "tool_output": return "完了";
    case "reasoning": return "分析中";
    case "text_delta": return "回答生成中";
    case "message_output": return "完了";
    default: return eventType;
  }
}

// ---------------------------------------------------------------------------
// ReasoningLine
// ---------------------------------------------------------------------------

function ReasoningLine({ content }: { content: string }) {
  return (
    <div className="flex items-start gap-2 min-w-0">
      <Brain className="w-3 h-3 shrink-0 mt-0.5 text-[#c0c4cc]" />
      <div className="min-w-0 text-[11px] text-[#9ca3af] leading-relaxed [&_p]:my-0.5 [&_ul]:my-0.5 [&_ol]:my-0.5 [&_li]:text-[11px] [&_li]:text-[#9ca3af] [&_strong]:text-[#7f8694] [&_*]:text-[11px] [&_p]:last:mb-0">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// TextSegment
// ---------------------------------------------------------------------------

function TextSegment({ content, isLast, isStreaming }: { content: string; isLast: boolean; isStreaming?: boolean }) {
  return (
    <div className="report-content overflow-hidden min-w-0">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
      {isLast && isStreaming && (
        <span className="inline-block w-0.5 h-5 bg-[#e94560] animate-pulse ml-0.5 align-middle rounded-full" />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ActivityGroupInline (collapsible)
// ---------------------------------------------------------------------------

function ActivityGroupInline({ items }: { items: ActivityItem[] }) {
  const [isOpen, setIsOpen] = useState(false);

  const toolCount = items.filter((it) => it.kind === "tool").length;
  const reasoningCount = items.filter((it) => it.kind === "reasoning").length;
  const subAgentCount = items.filter((it) => it.kind === "sub_agent").length;

  const parts: string[] = [];
  if (reasoningCount > 0) parts.push(`思考 ${reasoningCount}`);
  if (toolCount > 0) parts.push(`ツール ${toolCount}`);
  if (subAgentCount > 0) parts.push(`エージェント ${subAgentCount}`);
  const summaryLabel = parts.join(" · ");
  if (!summaryLabel) return null;

  return (
    <div>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="group inline-flex items-center gap-1 text-[11px] text-[#b0b5bd] hover:text-[#6b7280] transition-colors cursor-pointer"
      >
        <ChevronRight
          className={`w-2.5 h-2.5 transition-transform duration-150 ${
            isOpen ? "rotate-90" : ""
          }`}
        />
        <span className="tracking-wide">{summaryLabel}</span>
      </button>
      {isOpen && (
        <div className="mt-1.5 ml-[14px] border-l border-[#e5e7eb] pl-2.5">
          <ActivityItemsRenderer items={items} />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ActivityItemsRenderer
// ---------------------------------------------------------------------------

function ActivityItemsRenderer({
  items,
  isStreaming,
}: {
  items: ActivityItem[];
  isStreaming?: boolean;
}) {
  const groups = groupConsecutive(items);

  return (
    <div className="space-y-2">
      {groups.map((group, gi) => {
        if (group.kind === "reasoning") {
          return (
            <div key={`r-${gi}`} className="space-y-1.5">
              {group.items.map((item) => (
                <ReasoningLine
                  key={item.id}
                  content={(item as ReasoningActivityItem).content}
                />
              ))}
            </div>
          );
        }
        if (group.kind === "text") {
          return (
            <div key={`x-${gi}`}>
              {group.items.map((item, idx) => {
                const textItem = item as TextActivityItem;
                const isLastText = gi === groups.length - 1 && idx === group.items.length - 1;
                return (
                  <TextSegment
                    key={item.id}
                    content={textItem.content}
                    isLast={isLastText}
                    isStreaming={isStreaming}
                  />
                );
              })}
            </div>
          );
        }
        if (group.kind === "sub_agent") {
          return (
            <div key={`s-${gi}`} className="flex flex-wrap gap-1.5">
              {group.items.map((item) => (
                <SubAgentBadge key={item.id} item={item as SubAgentActivityItem} />
              ))}
            </div>
          );
        }
        if (group.kind === "tool") {
          return (
            <div key={`t-${gi}`} className="flex flex-wrap gap-1 sm:gap-1.5">
              {group.items.map((item) => (
                <ToolBadge key={item.id} item={item as ToolActivityItem} />
              ))}
            </div>
          );
        }
        return null;
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// InterleavedTimeline
// ---------------------------------------------------------------------------

function InterleavedTimeline({
  items,
  isStreaming,
}: {
  items: ActivityItem[];
  isStreaming?: boolean;
}) {
  if (!items || items.length === 0) return null;

  // Streaming: show full interleaved timeline
  if (isStreaming) {
    return (
      <div>
        <ActivityItemsRenderer
          items={items}
          isStreaming={isStreaming}
        />
      </div>
    );
  }

  // Completed: text always visible, reasoning/tools/sub_agent collapsed
  const sections = groupIntoSections(items);

  return (
    <div className="space-y-2">
      {sections.map((section, si) => {
        if (section.type === "activity") {
          return (
            <ActivityGroupInline key={`act-${si}`} items={section.items} />
          );
        }
        return (
          <div key={`cnt-${si}`}>
            <ActivityItemsRenderer items={section.items} />
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// UserMessage
// ---------------------------------------------------------------------------

function UserMessage({ message }: { message: Message }) {
  return (
    <div className="flex justify-end overflow-hidden">
      <div className="max-w-[85%] sm:max-w-[70%] min-w-0">
        <div className="bg-[#f0f1f5] text-[#1a1a2e] rounded-2xl px-4 py-2.5 text-[14px] sm:text-sm leading-relaxed">
          <p className="whitespace-pre-wrap break-words overflow-hidden">{message.content}</p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AssistantMessage
// ---------------------------------------------------------------------------

function AssistantMessage({ message }: { message: Message }) {
  const items = message.activityItems || [];
  const hasTextItems = items.some((it) => it.kind === "text");

  // Show thinking indicator when streaming started but no events yet
  const showThinking = !!message.isStreaming && items.length === 0 && !message.content;

  // New interleaved mode: text segments are in activityItems
  if (hasTextItems) {
    return (
      <div className="assistant-response overflow-hidden min-w-0">
        <InterleavedTimeline
          items={items}
          isStreaming={message.isStreaming}
        />
      </div>
    );
  }

  // Legacy mode or initial state
  return (
    <div className="assistant-response overflow-hidden min-w-0">
      {showThinking ? (
        <ThinkingIndicator />
      ) : (
        <>
          {/* Activity items first (for streaming) */}
          {items.length > 0 && (
            <div className="mb-2.5 sm:mb-3">
              <ActivityItemsRenderer
                items={items}
                isStreaming={message.isStreaming}
              />
            </div>
          )}

          {/* Text content */}
          {message.content && (
            <div className="report-content overflow-hidden min-w-0">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={markdownComponents}
              >
                {message.content}
              </ReactMarkdown>

              {message.isStreaming && (
                <span className="inline-block w-0.5 h-5 bg-[#e94560] animate-pulse ml-0.5 align-middle rounded-full" />
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.role === "user") {
    return <UserMessage message={message} />;
  }
  return <AssistantMessage message={message} />;
}
