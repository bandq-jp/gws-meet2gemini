"use client";

/**
 * ChatMessage Component
 *
 * Renders individual chat messages with sub-agent cards and activity timeline.
 * Based on ga4-oauth-aiagent with enhanced sub-agent visualization.
 */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import type { Components } from "react-markdown";
import { useState, useEffect } from "react";
import {
  Wrench,
  Loader2,
  BarChart3,
  Search,
  Database,
  ChevronDown,
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
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import { ThinkingIndicator } from "./ThinkingIndicator";
import type {
  Message,
  ActivityItem,
  TextActivityItem,
  ToolActivityItem,
  ReasoningActivityItem,
  SubAgentActivityItem,
  ChartActivityItem,
} from "@/lib/marketing/types";
import { ChartRenderer } from "./charts";

// ---------------------------------------------------------------------------
// Sub-agent configuration
// ---------------------------------------------------------------------------

type AgentUIConfig = {
  label: string;
  icon: typeof Bot;
  gradient: string;
  bgLight: string;
  textColor: string;
  borderColor: string;
  accentColor: string;
};

const SUB_AGENT_CONFIG: Record<string, AgentUIConfig> = {
  // Analytics Agent (GA4 + GSC)
  analyticsagent: {
    label: "Analytics",
    icon: BarChart3,
    gradient: "from-blue-500 to-cyan-500",
    bgLight: "bg-blue-50",
    textColor: "text-blue-700",
    borderColor: "border-blue-200",
    accentColor: "#3b82f6",
  },
  analytics: {
    label: "Analytics",
    icon: BarChart3,
    gradient: "from-blue-500 to-cyan-500",
    bgLight: "bg-blue-50",
    textColor: "text-blue-700",
    borderColor: "border-blue-200",
    accentColor: "#3b82f6",
  },
  // SEO Agent (Ahrefs)
  seoagent: {
    label: "SEO",
    icon: TrendingUp,
    gradient: "from-emerald-500 to-teal-500",
    bgLight: "bg-emerald-50",
    textColor: "text-emerald-700",
    borderColor: "border-emerald-200",
    accentColor: "#10b981",
  },
  seo: {
    label: "SEO",
    icon: TrendingUp,
    gradient: "from-emerald-500 to-teal-500",
    bgLight: "bg-emerald-50",
    textColor: "text-emerald-700",
    borderColor: "border-emerald-200",
    accentColor: "#10b981",
  },
  // Ad Platform Agent (Meta Ads)
  adplatformagent: {
    label: "Meta Ads",
    icon: Megaphone,
    gradient: "from-purple-500 to-pink-500",
    bgLight: "bg-purple-50",
    textColor: "text-purple-700",
    borderColor: "border-purple-200",
    accentColor: "#8b5cf6",
  },
  ad_platform: {
    label: "Meta Ads",
    icon: Megaphone,
    gradient: "from-purple-500 to-pink-500",
    bgLight: "bg-purple-50",
    textColor: "text-purple-700",
    borderColor: "border-purple-200",
    accentColor: "#8b5cf6",
  },
  // Zoho CRM Agent
  zohocrmagent: {
    label: "Zoho CRM",
    icon: Users,
    gradient: "from-orange-500 to-amber-500",
    bgLight: "bg-orange-50",
    textColor: "text-orange-700",
    borderColor: "border-orange-200",
    accentColor: "#f97316",
  },
  zoho_crm: {
    label: "Zoho CRM",
    icon: Users,
    gradient: "from-orange-500 to-amber-500",
    bgLight: "bg-orange-50",
    textColor: "text-orange-700",
    borderColor: "border-orange-200",
    accentColor: "#f97316",
  },
  // Candidate Insight Agent
  candidateinsightagent: {
    label: "Candidate Insight",
    icon: Users,
    gradient: "from-amber-500 to-yellow-500",
    bgLight: "bg-amber-50",
    textColor: "text-amber-700",
    borderColor: "border-amber-200",
    accentColor: "#f59e0b",
  },
  candidate_insight: {
    label: "Candidate Insight",
    icon: Users,
    gradient: "from-amber-500 to-yellow-500",
    bgLight: "bg-amber-50",
    textColor: "text-amber-700",
    borderColor: "border-amber-200",
    accentColor: "#f59e0b",
  },
  // WordPress Agent
  wordpressagent: {
    label: "WordPress",
    icon: FileText,
    gradient: "from-cyan-500 to-sky-500",
    bgLight: "bg-cyan-50",
    textColor: "text-cyan-700",
    borderColor: "border-cyan-200",
    accentColor: "#06b6d4",
  },
  wordpress: {
    label: "WordPress",
    icon: FileText,
    gradient: "from-cyan-500 to-sky-500",
    bgLight: "bg-cyan-50",
    textColor: "text-cyan-700",
    borderColor: "border-cyan-200",
    accentColor: "#06b6d4",
  },
  default: {
    label: "Agent",
    icon: Bot,
    gradient: "from-slate-500 to-gray-500",
    bgLight: "bg-slate-50",
    textColor: "text-slate-700",
    borderColor: "border-slate-200",
    accentColor: "#64748b",
  },
};

function getAgentConfig(agentName: string): AgentUIConfig {
  // Normalize: lowercase, remove non-alphanumeric chars except underscore
  const key = agentName.toLowerCase().replace(/[^a-z0-9_]/g, "");
  return SUB_AGENT_CONFIG[key] || SUB_AGENT_CONFIG.default;
}

// ---------------------------------------------------------------------------
// Tool metadata maps
// ---------------------------------------------------------------------------

const TOOL_ICONS: Record<string, typeof Wrench> = {
  run_report: BarChart3,
  run_realtime_report: BarChart3,
  get_search_analytics: Search,
  get_performance_overview: Search,
  list_properties: Database,
  search_job_seekers: Users,
  get_job_seeker_detail: Users,
  aggregate_by_channel: BarChart3,
  get_campaigns: Megaphone,
  get_adsets: Megaphone,
  list_posts: FileText,
  code_interpreter: Code2,
  web_search: Globe,
};

const TOOL_LABELS: Record<string, string> = {
  run_report: "レポート取得",
  run_realtime_report: "リアルタイム取得",
  get_search_analytics: "検索分析",
  get_performance_overview: "パフォーマンス概要",
  list_properties: "プロパティ一覧",
  search_job_seekers: "求職者検索",
  get_job_seeker_detail: "求職者詳細",
  aggregate_by_channel: "チャネル集計",
  get_campaigns: "キャンペーン取得",
  get_adsets: "広告セット取得",
  list_posts: "記事一覧",
  code_interpreter: "コード実行",
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
// SubAgentBadge - Inline badge for sub-agent (matches main agent tool style)
// ---------------------------------------------------------------------------

function SubAgentBadge({ item }: { item: SubAgentActivityItem }) {
  // Default expanded when running (user requested)
  const [isExpanded, setIsExpanded] = useState(item.isRunning);
  const config = getAgentConfig(item.agent);
  const Icon = config.icon;

  const toolCalls = item.toolCalls || [];
  const hasDetails = toolCalls.length > 0 || item.reasoningContent;

  // Auto-expand when running, auto-collapse after completion
  useEffect(() => {
    if (item.isRunning && hasDetails) {
      setIsExpanded(true);
    } else if (!item.isRunning) {
      // Auto-collapse 1 second after completion
      const timer = setTimeout(() => setIsExpanded(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [item.isRunning, hasDetails]);

  return (
    <div className="space-y-1.5">
      {/* Main badge - inline with other activity items */}
      <button
        onClick={() => hasDetails && setIsExpanded(!isExpanded)}
        className={`
          inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] sm:text-xs
          transition-all duration-200 cursor-pointer
          ${item.isRunning
            ? "bg-[#f0f1f5] text-[#374151] border border-[#e5e7eb]"
            : "bg-[#ecfdf5] text-[#065f46] border border-[#a7f3d0]"
          }
        `}
      >
        <Icon className="w-3 h-3 shrink-0" />
        <span className="font-medium">{config.label}</span>
        {item.isRunning ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <CheckCircle2 className="w-3 h-3 text-[#10b981]" />
        )}
        {hasDetails && (
          <span className="text-[#9ca3af] ml-0.5">
            {isExpanded ? "▼" : "▶"}
          </span>
        )}
      </button>

      {/* Expanded details - tool calls and reasoning (full content, no line-clamp) */}
      {isExpanded && hasDetails && (
        <div className="ml-3 pl-2.5 border-l border-[#e5e7eb] space-y-1.5">
          {/* Tool calls - chronological display */}
          {toolCalls.map((tc, idx) => {
            const ToolIcon = TOOL_ICONS[tc.toolName] || Wrench;
            const toolLabel = TOOL_LABELS[tc.toolName] || tc.toolName;
            return (
              <div
                key={tc.callId || idx}
                className={`
                  inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[10px]
                  ${tc.isComplete
                    ? "bg-[#ecfdf5] text-[#065f46]"
                    : "bg-[#f8f9fb] text-[#6b7280]"
                  }
                `}
              >
                <ToolIcon className="w-2.5 h-2.5 shrink-0" />
                <span className="truncate max-w-[200px]">{toolLabel}</span>
                {tc.isComplete ? (
                  <span className="text-[#10b981]">✓</span>
                ) : (
                  <Loader2 className="w-2.5 h-2.5 animate-spin" />
                )}
              </div>
            );
          })}

          {/* Reasoning - FULL content with markdown rendering (no line-clamp) */}
          {item.reasoningContent && (
            <div className="flex items-start gap-1.5">
              <Brain className="w-3 h-3 shrink-0 mt-0.5 text-[#c0c4cc]" />
              <div className="text-[10px] text-[#9ca3af] leading-relaxed [&_p]:my-0.5 [&_ul]:my-0.5 [&_ol]:my-0.5 [&_li]:text-[10px] [&_li]:text-[#9ca3af] [&_strong]:text-[#7f8694] [&_*]:text-[10px] [&_p]:last:mb-0">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {item.reasoningContent}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ToolBadge
// ---------------------------------------------------------------------------

function ToolBadge({ item }: { item: ToolActivityItem }) {
  const Icon = TOOL_ICONS[item.name] || Wrench;
  const label = TOOL_LABELS[item.name] || item.name;
  // Use output presence to determine status (undefined = running, string = complete)
  const isDone = !!item.output;

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

function TextSegment({
  content,
  isLast,
  isStreaming,
}: {
  content: string;
  isLast: boolean;
  isStreaming?: boolean;
}) {
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
// ActivityTimeline
// ---------------------------------------------------------------------------

function ActivityTimeline({
  items,
  isStreaming,
}: {
  items: ActivityItem[];
  isStreaming?: boolean;
}) {
  if (!items || items.length === 0) return null;

  // Sort by sequence and render in arrival order (interleaved timeline)
  const sortedItems = [...items].sort((a, b) => a.sequence - b.sequence);

  // Group consecutive items by kind for compact rendering
  const groups: { kind: string; items: ActivityItem[] }[] = [];
  for (const item of sortedItems) {
    const lastGroup = groups[groups.length - 1];
    // Group sub_agent and tool badges together; text and reasoning are individual
    const groupable = item.kind === "sub_agent" || item.kind === "tool";
    if (lastGroup && lastGroup.kind === item.kind && groupable) {
      lastGroup.items.push(item);
    } else {
      groups.push({ kind: item.kind, items: [item] });
    }
  }

  return (
    <div className="space-y-2.5">
      {groups.map((group, groupIdx) => {
        switch (group.kind) {
          case "sub_agent":
            return (
              <div key={groupIdx} className="flex flex-wrap gap-1.5">
                {group.items.map((item) => (
                  <SubAgentBadge
                    key={item.id}
                    item={item as SubAgentActivityItem}
                  />
                ))}
              </div>
            );

          case "tool":
            return (
              <div key={groupIdx} className="flex flex-wrap gap-1 sm:gap-1.5">
                {group.items.map((item) => (
                  <ToolBadge key={item.id} item={item as ToolActivityItem} />
                ))}
              </div>
            );

          case "reasoning":
            return (
              <div key={groupIdx} className="space-y-1.5">
                {group.items.map((item) => (
                  <ReasoningLine
                    key={item.id}
                    content={(item as ReasoningActivityItem).content}
                  />
                ))}
              </div>
            );

          case "text":
            return (
              <div key={groupIdx}>
                {group.items.map((item, idx) => (
                  <TextSegment
                    key={item.id}
                    content={(item as TextActivityItem).content}
                    isLast={
                      groupIdx === groups.length - 1 &&
                      idx === group.items.length - 1
                    }
                    isStreaming={isStreaming}
                  />
                ))}
              </div>
            );

          case "chart":
            return (
              <div key={groupIdx} className="space-y-2">
                {group.items.map((item) => (
                  <ChartRenderer
                    key={item.id}
                    spec={(item as ChartActivityItem).spec}
                  />
                ))}
              </div>
            );

          default:
            return null;
        }
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
          <p className="whitespace-pre-wrap break-words overflow-hidden">
            {message.content}
          </p>
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
  const hasItems = items.length > 0;

  // Show thinking indicator when streaming started but no events yet
  const showThinking = !!message.isStreaming && !hasItems && !message.content;

  return (
    <div className="assistant-response overflow-hidden min-w-0">
      {showThinking ? (
        <ThinkingIndicator />
      ) : hasItems ? (
        <ActivityTimeline items={items} isStreaming={message.isStreaming} />
      ) : message.content ? (
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
      ) : null}
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
