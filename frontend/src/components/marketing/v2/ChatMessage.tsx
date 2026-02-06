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
import { useState, useEffect, useCallback, memo, useMemo, useRef } from "react";
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
  Target,
  Copy,
  Check,
  Image as ImageIcon,
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
  CodeExecutionActivityItem,
  CodeResultActivityItem,
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
  // Company Database Agent
  companydatabaseagent: {
    label: "企業DB",
    icon: Database,
    gradient: "from-indigo-500 to-blue-500",
    bgLight: "bg-indigo-50",
    textColor: "text-indigo-700",
    borderColor: "border-indigo-200",
    accentColor: "#6366f1",
  },
  company_database: {
    label: "企業DB",
    icon: Database,
    gradient: "from-indigo-500 to-blue-500",
    bgLight: "bg-indigo-50",
    textColor: "text-indigo-700",
    borderColor: "border-indigo-200",
    accentColor: "#6366f1",
  },
  // CA Support Agent
  casupportagent: {
    label: "CA支援",
    icon: Users,
    gradient: "from-rose-500 to-pink-500",
    bgLight: "bg-rose-50",
    textColor: "text-rose-700",
    borderColor: "border-rose-200",
    accentColor: "#f43f5e",
  },
  ca_support: {
    label: "CA支援",
    icon: Users,
    gradient: "from-rose-500 to-pink-500",
    bgLight: "bg-rose-50",
    textColor: "text-rose-700",
    borderColor: "border-rose-200",
    accentColor: "#f43f5e",
  },
  // Google Search Agent
  googlesearchagent: {
    label: "Google検索",
    icon: Globe,
    gradient: "from-sky-500 to-blue-500",
    bgLight: "bg-sky-50",
    textColor: "text-sky-700",
    borderColor: "border-sky-200",
    accentColor: "#0ea5e9",
  },
  google_search: {
    label: "Google検索",
    icon: Globe,
    gradient: "from-sky-500 to-blue-500",
    bgLight: "bg-sky-50",
    textColor: "text-sky-700",
    borderColor: "border-sky-200",
    accentColor: "#0ea5e9",
  },
  // Code Execution Agent
  codeexecutionagent: {
    label: "コード実行",
    icon: Code2,
    gradient: "from-violet-500 to-purple-500",
    bgLight: "bg-violet-50",
    textColor: "text-violet-700",
    borderColor: "border-violet-200",
    accentColor: "#8b5cf6",
  },
  code_execution: {
    label: "コード実行",
    icon: Code2,
    gradient: "from-violet-500 to-purple-500",
    bgLight: "bg-violet-50",
    textColor: "text-violet-700",
    borderColor: "border-violet-200",
    accentColor: "#8b5cf6",
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
  // Analytics (GA4/GSC)
  run_report: BarChart3,
  run_realtime_report: BarChart3,
  get_search_analytics: Search,
  get_performance_overview: Search,
  list_properties: Database,
  // Zoho CRM
  search_job_seekers: Users,
  get_job_seeker_detail: Users,
  aggregate_by_channel: BarChart3,
  // Meta Ads
  get_campaigns: Megaphone,
  get_adsets: Megaphone,
  // WordPress
  list_posts: FileText,
  // Company DB
  get_company_detail: Database,
  search_companies: Search,
  get_company_definitions: Database,
  get_appeal_points: Target,
  match_companies_for_candidate: Users,
  get_pic_recommendations: Users,
  compare_companies: BarChart3,
  semantic_search_companies: Search,
  find_companies_for_candidate: Users,
  // Candidate Insight
  analyze_competitor_risk: TrendingUp,
  assess_urgency: TrendingUp,
  analyze_career_pattern: Users,
  generate_briefing: FileText,
  // Meeting
  search_meeting_notes: FileText,
  get_meeting_text: FileText,
  get_structured_data: Database,
  get_integrated_profile: Users,
  // General
  code_interpreter: Code2,
  web_search: Globe,
  render_chart: BarChart3,
};

const TOOL_LABELS: Record<string, string> = {
  // Analytics
  run_report: "レポート取得",
  run_realtime_report: "リアルタイム取得",
  get_search_analytics: "検索分析",
  get_performance_overview: "パフォーマンス概要",
  list_properties: "プロパティ一覧",
  // Zoho CRM
  search_job_seekers: "求職者検索",
  get_job_seeker_detail: "求職者詳細",
  aggregate_by_channel: "チャネル集計",
  // Meta Ads
  get_campaigns: "キャンペーン取得",
  get_adsets: "広告セット取得",
  // WordPress
  list_posts: "記事一覧",
  // Company DB
  get_company_detail: "企業詳細",
  search_companies: "企業検索",
  get_company_definitions: "企業一覧",
  get_appeal_points: "訴求ポイント",
  match_companies_for_candidate: "候補者マッチング",
  get_pic_recommendations: "担当者推奨",
  compare_companies: "企業比較",
  semantic_search_companies: "セマンティック検索",
  find_companies_for_candidate: "候補者向け企業検索",
  // Candidate Insight
  analyze_competitor_risk: "競合リスク分析",
  assess_urgency: "緊急度評価",
  analyze_career_pattern: "キャリアパターン",
  generate_briefing: "ブリーフィング",
  // Meeting
  search_meeting_notes: "議事録検索",
  get_meeting_text: "議事録本文",
  get_structured_data: "構造化データ",
  get_integrated_profile: "統合プロファイル",
  // General
  code_interpreter: "コード実行",
  web_search: "Web検索",
  render_chart: "チャート作成",
};

/**
 * Extract contextual label from tool arguments.
 * e.g., get_company_detail({company_name: "株式会社MyVision"}) → "株式会社MyVision"
 */
function extractToolContext(toolName: string, argsJson?: string): string | null {
  if (!argsJson) return null;
  try {
    const args = JSON.parse(argsJson);
    // Company name
    if (args.company_name) return args.company_name;
    // Search query
    if (args.query && typeof args.query === "string") return args.query.slice(0, 40);
    // Candidate reasons (for find_companies_for_candidate)
    if (args.reasons && typeof args.reasons === "string") return args.reasons.slice(0, 40);
    // Job seeker search
    if (args.name) return args.name;
    // Meeting search
    if (args.keyword) return args.keyword;
    return null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// CodeBlock with copy button (U-4)
// ---------------------------------------------------------------------------

function CodeBlock({ language, children }: { language: string; children: React.ReactNode }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    const text = typeof children === "string" ? children : String(children ?? "");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [children]);

  return (
    <div className="my-2.5 sm:my-3 rounded-lg bg-[#1a1a2e] overflow-hidden group relative">
      <div className="flex items-center justify-between px-3 sm:px-4 py-1.5 bg-[#2a2a4e]">
        <span className="text-[10px] text-[#9ca3af] uppercase tracking-wider font-medium">
          {language}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[10px] text-[#9ca3af] hover:text-white transition-colors"
          aria-label="コピー"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" />
              <span>コピー済み</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>コピー</span>
            </>
          )}
        </button>
      </div>
      <pre className="px-3 sm:px-4 py-2.5 sm:py-3 overflow-x-auto text-[11px] sm:text-xs leading-relaxed">
        <code className="text-[#e5e7eb]">{children}</code>
      </pre>
    </div>
  );
}

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
        <CodeBlock language={className?.replace("language-", "") || "code"}>
          {children}
        </CodeBlock>
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

// Progress labels for each agent type - detailed phase-based labels
const AGENT_PROGRESS_LABELS: Record<string, string[]> = {
  analytics: ["GA4に接続中", "データを取得中", "メトリクスを分析中", "レポートを生成中"],
  seo: ["Ahrefsに接続中", "バックリンクを確認中", "キーワードを分析中", "競合を調査中"],
  ad_platform: ["Meta APIに接続中", "キャンペーンを取得中", "パフォーマンスを分析中", "インサイトを抽出中"],
  zoho_crm: ["CRMに接続中", "候補者を検索中", "データを集計中", "レポートを作成中"],
  candidate_insight: ["データを統合中", "リスクを評価中", "緊急度を分析中", "ブリーフィングを生成中"],
  wordpress: ["WordPressに接続中", "記事を検索中", "コンテンツを取得中", "メタ情報を確認中"],
  company_database: ["企業DBを検索中", "企業情報を取得中", "マッチングを実行中", "結果を整理中"],
  ca_support: ["データを統合中", "候補者情報を収集中", "企業情報を確認中", "分析レポートを作成中"],
  google_search: ["検索クエリを構築中", "Google検索を実行中", "結果を収集中", "情報を統合中"],
  googlesearchagent: ["検索クエリを構築中", "Google検索を実行中", "結果を収集中", "情報を統合中"],
  code_execution: ["コードを生成中", "Pythonを実行中", "結果を処理中", "出力を整理中"],
  codeexecutionagent: ["コードを生成中", "Pythonを実行中", "結果を処理中", "出力を整理中"],
  default: ["準備中", "データを取得中", "処理中", "結果を整理中"],
};

// Sub-agent execution states for state machine visualization
type SubAgentState = "pending" | "thinking" | "executing" | "outputting" | "complete" | "error";

function getSubAgentState(item: SubAgentActivityItem): SubAgentState {
  if (!item.isRunning) {
    // Check for errors
    const hasError = item.toolCalls?.some(tc => tc.error);
    return hasError ? "error" : "complete";
  }

  // Running - determine phase
  const toolCalls = item.toolCalls || [];
  const runningTools = toolCalls.filter(tc => !tc.isComplete).length;
  const hasReasoning = !!item.reasoningContent;
  const hasOutput = !!item.outputPreview;

  if (hasOutput) return "outputting";
  if (runningTools > 0) return "executing";
  if (hasReasoning) return "thinking";
  return "pending";
}

// State icons and colors for state machine visualization
const STATE_CONFIG: Record<SubAgentState, { icon: string; label: string; color: string }> = {
  pending: { icon: "○", label: "準備中", color: "text-[#9ca3af]" },
  thinking: { icon: "◐", label: "思考中", color: "text-[#f59e0b]" },
  executing: { icon: "◑", label: "実行中", color: "text-[#3b82f6]" },
  outputting: { icon: "◕", label: "出力中", color: "text-[#8b5cf6]" },
  complete: { icon: "●", label: "完了", color: "text-[#10b981]" },
  error: { icon: "✗", label: "エラー", color: "text-[#dc2626]" },
};

function SubAgentBadge({ item }: { item: SubAgentActivityItem }) {
  // Default expanded when running or has details (user requested: no auto-collapse)
  const [isExpanded, setIsExpanded] = useState(item.isRunning);
  const [progressLabelIndex, setProgressLabelIndex] = useState(0);
  const config = getAgentConfig(item.agent);
  const Icon = config.icon;

  const toolCalls = item.toolCalls || [];
  const hasDetails = toolCalls.length > 0 || item.reasoningContent;
  const runningToolCount = toolCalls.filter(tc => !tc.isComplete).length;
  const completedToolCount = toolCalls.filter(tc => tc.isComplete && !tc.error).length;
  const errorCount = toolCalls.filter(tc => tc.error).length;

  // Get state machine state
  const state = getSubAgentState(item);
  const stateConfig = STATE_CONFIG[state];

  // Extract first sentence of reasoning for preview chip
  const reasoningPreview = item.reasoningContent
    ? item.reasoningContent.split(/[。.!！?\?]/)[0]?.trim()?.slice(0, 50) + (item.reasoningContent.length > 50 ? "..." : "")
    : null;

  // Rotate progress labels every 2.5 seconds when running (faster rotation for better feedback)
  useEffect(() => {
    if (!item.isRunning) return;

    const agentKey = item.agent.toLowerCase().replace(/[^a-z0-9_]/g, "");
    const labels = AGENT_PROGRESS_LABELS[agentKey] || AGENT_PROGRESS_LABELS.default;

    const interval = setInterval(() => {
      setProgressLabelIndex((prev) => (prev + 1) % labels.length);
    }, 2500);

    return () => clearInterval(interval);
  }, [item.isRunning, item.agent]);

  // Auto-expand when running with details (NO auto-collapse - user keeps control)
  useEffect(() => {
    if (item.isRunning && hasDetails) {
      setIsExpanded(true);
    }
    // Removed auto-collapse: users prefer to see details after completion
  }, [item.isRunning, hasDetails]);

  // Get current progress label
  const agentKey = item.agent.toLowerCase().replace(/[^a-z0-9_]/g, "");
  const labels = AGENT_PROGRESS_LABELS[agentKey] || AGENT_PROGRESS_LABELS.default;
  const progressLabel = labels[progressLabelIndex % labels.length];

  return (
    <div className="space-y-1.5">
      {/* Main badge - inline with other activity items */}
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          onClick={() => hasDetails && setIsExpanded(!isExpanded)}
          className={`
            inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] sm:text-xs
            transition-all duration-300 cursor-pointer
            ${state === "error"
              ? "bg-[#fef2f2] text-[#dc2626] border border-[#fecaca]"
              : state === "complete"
                ? "bg-[#ecfdf5] text-[#065f46] border border-[#a7f3d0]"
                : "bg-[#f0f1f5] text-[#374151] border border-[#e5e7eb]"
            }
          `}
        >
          <Icon className="w-3 h-3 shrink-0" />
          <span className="font-medium">{config.label}</span>

          {/* State machine indicator */}
          <span className={`text-[10px] ${stateConfig.color} font-medium`}>
            {stateConfig.icon}
          </span>

          {/* Status details */}
          {item.isRunning ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin text-[#6b7280]" />
              {/* Progress label - shows what the agent is doing */}
              <span className="text-[10px] text-[#9ca3af] ml-0.5 hidden sm:inline transition-opacity duration-300">
                {progressLabel}
              </span>
              {/* Running tool count indicator */}
              {runningToolCount > 0 && (
                <span className="text-[10px] text-[#3b82f6] ml-0.5 hidden sm:inline">
                  [{runningToolCount}実行中]
                </span>
              )}
            </>
          ) : (
            <>
              {/* Show tool count and status when completed */}
              {completedToolCount > 0 && (
                <span className="text-[10px] text-[#10b981] ml-0.5">
                  {completedToolCount}件
                </span>
              )}
              {errorCount > 0 && (
                <span className="text-[10px] text-[#dc2626] ml-0.5">
                  {errorCount}件エラー
                </span>
              )}
            </>
          )}

          {/* Expand/collapse indicator */}
          {hasDetails && (
            <span className="text-[#9ca3af] ml-0.5 text-[10px]">
              {isExpanded ? "▼" : "▶"}
            </span>
          )}
        </button>

        {/* Reasoning preview chip - shown when collapsed and has reasoning */}
        {!isExpanded && reasoningPreview && (
          <span className="text-[10px] text-[#9ca3af] bg-[#f8f9fb] px-2 py-0.5 rounded-full max-w-[200px] truncate hidden sm:inline">
            💭 {reasoningPreview}
          </span>
        )}
      </div>

      {/* Expanded details - tool calls and reasoning (full content, no line-clamp) */}
      {isExpanded && hasDetails && (
        <div className="ml-3 pl-2.5 border-l-2 border-[#e5e7eb] space-y-2 animate-in slide-in-from-top-1 duration-200">
          {/* Progress bar for tool execution (visual timeline) */}
          {toolCalls.length > 0 && (
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-[#f0f1f5] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#3b82f6] to-[#10b981] rounded-full transition-all duration-500"
                  style={{
                    width: `${toolCalls.length > 0 ? (completedToolCount / toolCalls.length) * 100 : 0}%`,
                  }}
                />
              </div>
              <span className="text-[9px] text-[#9ca3af] whitespace-nowrap">
                {completedToolCount}/{toolCalls.length}
              </span>
            </div>
          )}

          {/* Tool calls - chronological display with timeline dots */}
          {toolCalls.map((tc, idx) => {
            const ToolIcon = TOOL_ICONS[tc.toolName] || Wrench;
            const toolLabel = TOOL_LABELS[tc.toolName] || tc.toolName;
            const contextLabel = extractToolContext(tc.toolName, tc.arguments);
            const hasError = !!tc.error;
            const isLast = idx === toolCalls.length - 1;
            return (
              <div key={tc.callId || idx} className="flex items-start gap-2">
                {/* Timeline dot */}
                <div className="flex flex-col items-center">
                  <div
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      hasError
                        ? "bg-[#dc2626]"
                        : tc.isComplete
                          ? "bg-[#10b981]"
                          : "bg-[#3b82f6] animate-pulse"
                    }`}
                  />
                  {!isLast && <div className="w-px h-4 bg-[#e5e7eb]" />}
                </div>
                {/* Tool info */}
                <div className="flex-1 -mt-0.5 space-y-0.5">
                  <div
                    className={`
                      inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[10px]
                      transition-all duration-200
                      ${hasError
                        ? "bg-[#fef2f2] text-[#dc2626] border border-[#fecaca]"
                        : tc.isComplete
                          ? "bg-[#ecfdf5] text-[#065f46]"
                          : "bg-[#f8f9fb] text-[#6b7280]"
                      }
                    `}
                  >
                    <ToolIcon className="w-2.5 h-2.5 shrink-0" />
                    <span className="truncate max-w-[120px]">{toolLabel}</span>
                    {/* Contextual detail from tool arguments */}
                    {contextLabel && (
                      <span className="text-[9px] text-[#9ca3af] truncate max-w-[150px] hidden sm:inline">
                        {contextLabel}
                      </span>
                    )}
                    {hasError ? (
                      <span className="text-[#dc2626]">✗</span>
                    ) : tc.isComplete ? (
                      <span className="text-[#10b981]">✓</span>
                    ) : (
                      <Loader2 className="w-2.5 h-2.5 animate-spin" />
                    )}
                  </div>
                  {hasError && (
                    <div className="text-[9px] text-[#dc2626] truncate max-w-[250px]">
                      {tc.error}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Reasoning - FULL content with markdown rendering (no line-clamp) */}
          {item.reasoningContent && (
            <div className="flex items-start gap-1.5 mt-1">
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

  // Sort by sequence and render in arrival order (interleaved timeline) (U-12: memoized)
  const sortedItems = useMemo(
    () => [...items].sort((a, b) => a.sequence - b.sequence),
    [items]
  );

  // Group consecutive items by kind for compact rendering
  const groups: { kind: string; items: ActivityItem[] }[] = [];
  for (const item of sortedItems) {
    const lastGroup = groups[groups.length - 1];
    // Group consecutive items of same kind:
    // - text: concatenated for seamless markdown rendering (prevents mid-sentence breaks)
    // - sub_agent/tool: rendered as badge rows
    // - reasoning: individual items (separate expandable blocks)
    // - chart: individual items (separate visualizations)
    const groupable =
      item.kind === "text" || item.kind === "sub_agent" || item.kind === "tool";
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

          case "text": {
            // Concatenate all text items in this group into a single string
            // This prevents visual line breaks between consecutive text chunks
            const combinedContent = group.items
              .map((item) => (item as TextActivityItem).content)
              .join("");
            return (
              <TextSegment
                key={groupIdx}
                content={combinedContent}
                isLast={groupIdx === groups.length - 1}
                isStreaming={isStreaming}
              />
            );
          }

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

          case "code_execution":
            return (
              <div key={groupIdx} className="space-y-1">
                {group.items.map((item) => {
                  const codeItem = item as CodeExecutionActivityItem;
                  return (
                    <CodeBlock
                      key={item.id}
                      language={codeItem.language?.toLowerCase() || "python"}
                    >
                      {codeItem.code}
                    </CodeBlock>
                  );
                })}
              </div>
            );

          case "code_result":
            return (
              <div key={groupIdx} className="space-y-1">
                {group.items.map((item) => {
                  const resultItem = item as CodeResultActivityItem;
                  const isError =
                    resultItem.outcome === "OUTCOME_FAILED" ||
                    resultItem.outcome === "OUTCOME_DEADLINE_EXCEEDED";
                  return (
                    <div
                      key={item.id}
                      className={`my-1.5 rounded-lg border overflow-hidden ${
                        isError
                          ? "border-red-200 bg-red-50"
                          : "border-emerald-200 bg-emerald-50"
                      }`}
                    >
                      <div
                        className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium ${
                          isError ? "text-red-700" : "text-emerald-700"
                        }`}
                      >
                        {isError ? (
                          <span>実行エラー</span>
                        ) : (
                          <>
                            <CheckCircle2 className="w-3 h-3" />
                            <span>実行結果</span>
                          </>
                        )}
                      </div>
                      {resultItem.output && (
                        <pre
                          className={`px-3 py-2 text-[11px] sm:text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap ${
                            isError ? "text-red-800" : "text-emerald-900"
                          }`}
                        >
                          {resultItem.output}
                        </pre>
                      )}
                    </div>
                  );
                })}
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
  const attachments = message.attachments;
  return (
    <div className="flex justify-end overflow-hidden">
      <div className="max-w-[85%] sm:max-w-[70%] min-w-0">
        {/* Attachment badges */}
        {attachments && attachments.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-1.5 justify-end">
            {attachments.map((att, idx) => {
              const isImage = att.mime_type.startsWith("image/");
              return (
                <div
                  key={`${att.filename}-${idx}`}
                  className="inline-flex items-center gap-1.5 bg-[#e8eaed] rounded-lg px-2 py-1 text-[10px] text-[#374151]"
                >
                  {isImage ? (
                    <ImageIcon className="w-3 h-3 text-[#9ca3af]" />
                  ) : (
                    <FileText className="w-3 h-3 text-[#9ca3af]" />
                  )}
                  <span className="truncate max-w-[120px]">{att.filename}</span>
                </div>
              );
            })}
          </div>
        )}
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
        <ThinkingIndicator progressText={message.progressText} />
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

export const ChatMessage = memo(function ChatMessage({ message }: ChatMessageProps) {
  if (message.role === "user") {
    return <UserMessage message={message} />;
  }
  return <AssistantMessage message={message} />;
});
