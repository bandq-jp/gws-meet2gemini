"use client";

/**
 * FBレビュー ダッシュボード
 *
 * 会話ごとのフィードバック・アノテーション閲覧。
 * 左パネル: 会話リスト（KPI・フィルタ付き）
 * 右パネル: 選択した会話の詳細（FB/アノテーション、ユーザー別タブ）
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ThumbsUp,
  ThumbsDown,
  Download,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
  MessageSquare,
  Eye,
  ExternalLink,
  Pencil,
  AlertCircle,
  Info,
  Sparkles,
  User,
  Users,
  Search,
  FileText,
  ArrowLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useFeedbackDashboard } from "@/hooks/use-feedback";
import type {
  ConversationFeedbackSummary,
  MessageFeedback,
  MessageAnnotation,
  ReviewStatus,
  AnnotationSeverity,
} from "@/lib/feedback/types";

// ─── Token management ───
type TokenState = { secret: string | null; expiresAt: number };

// ─── Severity design tokens ───
const SEV: Record<AnnotationSeverity, { label: string; bg: string; text: string; dot: string }> = {
  critical: { label: "重大", bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
  major:    { label: "中程度", bg: "bg-orange-50", text: "text-orange-700", dot: "bg-orange-500" },
  minor:    { label: "軽微", bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-400" },
  info:     { label: "情報", bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  positive: { label: "良い点", bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
};

// ─── Status badge ───
function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "new": return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200 text-[10px] px-1.5 py-0">新規</Badge>;
    case "reviewed": return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-[10px] px-1.5 py-0">レビュー済</Badge>;
    case "actioned": return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-[10px] px-1.5 py-0">対応済</Badge>;
    case "dismissed": return <Badge variant="outline" className="bg-gray-50 text-gray-500 border-gray-200 text-[10px] px-1.5 py-0">却下</Badge>;
    default: return <Badge variant="outline" className="text-[10px] px-1.5 py-0">{status}</Badge>;
  }
}

// ════════════════════════════════════════════════════════════
// Main Page
// ════════════════════════════════════════════════════════════

export default function FeedbackPage() {
  const tokenRef = useRef<TokenState>({ secret: null, expiresAt: 0 });

  const ensureClientSecret = useCallback(async (): Promise<string> => {
    const now = Date.now();
    if (tokenRef.current.secret && tokenRef.current.expiresAt - 5_000 > now) {
      return tokenRef.current.secret;
    }
    const hasSecret = Boolean(tokenRef.current.secret);
    const endpoint = hasSecret
      ? "/api/marketing-v2/chatkit/refresh"
      : "/api/marketing-v2/chatkit/start";
    const response = await fetch(endpoint, {
      method: "POST",
      body: hasSecret ? JSON.stringify({ currentClientSecret: tokenRef.current.secret }) : undefined,
      headers: hasSecret ? { "Content-Type": "application/json" } : undefined,
    });
    if (!response.ok) throw new Error("Failed to fetch client secret");
    const data = await response.json();
    tokenRef.current = {
      secret: data.client_secret,
      expiresAt: now + (data.expires_in ?? 900) * 1000,
    };
    return tokenRef.current.secret!;
  }, []);

  const getClientSecret = useCallback(() => tokenRef.current.secret, []);

  const {
    overview,
    conversations,
    conversationDetail,
    conversationUsers,
    loading,
    detailLoading,
    loadOverview,
    loadConversations,
    loadConversationDetail,
    loadConversationUsers,
    updateReview,
    exportFeedback,
  } = useFeedbackDashboard(getClientSecret);

  // ─── State ───
  const [ratingFilter, setRatingFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [convPage, setConvPage] = useState(1);
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [selectedUserFilter, setSelectedUserFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // ─── Initial load ───
  useEffect(() => {
    (async () => {
      await ensureClientSecret();
      loadOverview();
      loadConversations({ page: 1 });
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Reload conversations when filters change ───
  useEffect(() => {
    if (!tokenRef.current.secret) return;
    loadConversations({
      page: convPage,
      rating: ratingFilter || undefined,
      user_email: userFilter || undefined,
    });
  }, [convPage, ratingFilter, userFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Load detail when conversation selected ───
  useEffect(() => {
    if (!selectedConvId || !tokenRef.current.secret) return;
    loadConversationDetail(selectedConvId, selectedUserFilter || undefined);
    loadConversationUsers(selectedConvId);
  }, [selectedConvId, selectedUserFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectConversation = (convId: string) => {
    setSelectedConvId(convId);
    setSelectedUserFilter("");
  };

  const handleExport = async (format: "jsonl" | "csv") => {
    await ensureClientSecret();
    await exportFeedback(format, {
      rating: ratingFilter || undefined,
      user_email: userFilter || undefined,
      conversation_id: selectedConvId || undefined,
    });
  };

  // Selected conversation summary
  const selectedConv = useMemo(
    () => conversations?.items.find(c => c.conversation_id === selectedConvId) ?? null,
    [conversations, selectedConvId],
  );

  // Filter conversations by search query (client-side)
  const filteredConversations = useMemo(() => {
    if (!conversations?.items || !searchQuery.trim()) return conversations?.items ?? [];
    const q = searchQuery.toLowerCase();
    return conversations.items.filter(c =>
      c.title.toLowerCase().includes(q) ||
      c.owner_email.toLowerCase().includes(q)
    );
  }, [conversations, searchQuery]);

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-white to-slate-50/80">
      {/* ─── Header ─── */}
      <div className="shrink-0 px-3 sm:px-6 py-3 sm:py-4 border-b border-border/50 bg-white/80 backdrop-blur-sm">
        <div className="flex items-center justify-between max-w-[1400px] mx-auto gap-2">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <SidebarTrigger className="md:hidden shrink-0" />
            <div className="w-8 h-8 rounded-lg bg-[var(--brand-100)]/50 flex items-center justify-center shrink-0 hidden sm:flex">
              <FileText className="w-4 h-4 text-[var(--brand-400)]" />
            </div>
            <div className="min-w-0">
              <h1 className="text-[14px] sm:text-[15px] font-semibold tracking-tight">FBレビュー</h1>
              <p className="text-[10px] sm:text-[11px] text-muted-foreground hidden sm:block">会話ごとのフィードバック・アノテーション管理</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {(ratingFilter || userFilter || selectedConvId) && (
              <span className="text-[10px] text-muted-foreground/60 hidden sm:inline">
                フィルタ適用中
              </span>
            )}
            <Button variant="outline" size="sm" className="h-7 text-[11px] gap-1" onClick={() => handleExport("csv")}>
              <Download className="w-3 h-3" /> <span className="hidden sm:inline">CSV</span>
            </Button>
            <Button variant="outline" size="sm" className="h-7 text-[11px] gap-1" onClick={() => handleExport("jsonl")}>
              <Download className="w-3 h-3" /> <span className="hidden sm:inline">JSONL</span>
            </Button>
          </div>
        </div>
      </div>

      {/* ─── KPI Cards ─── */}
      {overview && (
        <div className="shrink-0 px-3 sm:px-6 py-2 sm:py-3 border-b border-border/30">
          <div className="max-w-[1400px] mx-auto grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
            <KPICard icon={MessageSquare} label="合計FB" value={overview.total} />
            <KPICard icon={ThumbsUp} label="Good" value={overview.good} sub={`${overview.good_pct}%`} color="emerald" />
            <KPICard icon={ThumbsDown} label="Bad" value={overview.bad} sub={`${overview.bad_pct}%`} color="red" />
            <KPICard icon={Clock} label="未レビュー" value={overview.unreviewed} color="amber" />
          </div>
        </div>
      )}

      {/* ─── Two-Panel Layout ─── */}
      <div className="flex-1 flex overflow-hidden max-w-[1400px] mx-auto w-full relative">
        {/* ── Left Panel: Conversation List ── */}
        <div className={`w-full md:w-[380px] shrink-0 md:border-r border-border/40 flex flex-col bg-white/60 ${selectedConvId ? "hidden md:flex" : "flex"}`}>
          {/* Search + Filters */}
          <div className="shrink-0 p-3 space-y-2 border-b border-border/30">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/50" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="会話を検索..."
                className="w-full h-8 pl-8 pr-3 text-[12px] rounded-md border border-border/50 bg-white focus:outline-none focus:ring-1 focus:ring-[var(--brand-300)] placeholder:text-muted-foreground/40"
              />
            </div>
            <div className="flex gap-2">
              <Select value={ratingFilter || "all"} onValueChange={v => { setRatingFilter(v === "all" ? "" : v); setConvPage(1); }}>
                <SelectTrigger className="h-7 text-[11px] flex-1"><SelectValue placeholder="評価" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全ての評価</SelectItem>
                  <SelectItem value="good">Good のみ</SelectItem>
                  <SelectItem value="bad">Bad のみ</SelectItem>
                </SelectContent>
              </Select>
              <Select value={userFilter || "all"} onValueChange={v => { setUserFilter(v === "all" ? "" : v); setConvPage(1); }}>
                <SelectTrigger className="h-7 text-[11px] flex-1"><SelectValue placeholder="ユーザー" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全ユーザー</SelectItem>
                  {/* Dynamic user list from conversationUsers if available */}
                  {conversationUsers.map(u => (
                    <SelectItem key={u} value={u}>{u.split("@")[0]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Conversation Cards */}
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {loading && !conversations && (
              <div className="flex items-center justify-center h-32 text-[12px] text-muted-foreground">読み込み中...</div>
            )}
            {filteredConversations.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center h-32 text-[12px] text-muted-foreground">
                <MessageSquare className="w-5 h-5 mb-2 text-muted-foreground/30" />
                FBのある会話がありません
              </div>
            )}
            {filteredConversations.map(conv => (
              <ConversationCard
                key={conv.conversation_id}
                conv={conv}
                isSelected={selectedConvId === conv.conversation_id}
                onClick={() => handleSelectConversation(conv.conversation_id)}
              />
            ))}
          </div>

          {/* Pagination */}
          {conversations && conversations.total_pages > 1 && (
            <div className="shrink-0 flex items-center justify-between px-3 py-2 border-t border-border/30 bg-white/80">
              <span className="text-[10px] text-muted-foreground">
                {conversations.total}件中 {(convPage - 1) * conversations.per_page + 1}-{Math.min(convPage * conversations.per_page, conversations.total)}
              </span>
              <div className="flex gap-1">
                <Button variant="outline" size="icon" className="h-6 w-6" disabled={convPage <= 1} onClick={() => setConvPage(p => p - 1)}>
                  <ChevronLeft className="w-3 h-3" />
                </Button>
                <span className="text-[10px] px-1.5 flex items-center text-muted-foreground">{convPage}/{conversations.total_pages}</span>
                <Button variant="outline" size="icon" className="h-6 w-6" disabled={convPage >= conversations.total_pages} onClick={() => setConvPage(p => p + 1)}>
                  <ChevronRight className="w-3 h-3" />
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* ── Right Panel: Conversation Detail ── */}
        <div className={`flex-1 flex flex-col overflow-hidden bg-white/40 ${selectedConvId ? "absolute inset-0 md:relative md:inset-auto z-10 bg-white md:bg-white/40" : "hidden md:flex"}`}>
          {!selectedConvId ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground/50">
              <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center mb-4">
                <Eye className="w-6 h-6 text-slate-200" />
              </div>
              <p className="text-[13px]">左のリストから会話を選択</p>
              <p className="text-[11px] mt-1">フィードバックとアノテーションの詳細を表示します</p>
            </div>
          ) : (
            <>
              {/* Detail Header */}
              <div className="shrink-0 px-3 sm:px-5 py-3 border-b border-border/30 bg-white/80">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {/* Mobile back button */}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="md:hidden shrink-0 h-8 w-8"
                      onClick={() => setSelectedConvId(null)}
                    >
                      <ArrowLeft className="w-4 h-4" />
                    </Button>
                    <div className="min-w-0 flex-1">
                      <h2 className="text-[13px] font-semibold truncate">
                        {selectedConv?.title || selectedConvId.slice(0, 12)}
                      </h2>
                      <div className="flex items-center gap-2 sm:gap-3 mt-0.5 flex-wrap">
                        <span className="text-[10px] text-muted-foreground">
                          {selectedConv?.owner_email?.split("@")[0]}
                        </span>
                        {selectedConv && (
                          <div className="flex items-center gap-2 text-[10px]">
                            <span className="text-emerald-600">{selectedConv.good_count} Good</span>
                            <span className="text-red-500">{selectedConv.bad_count} Bad</span>
                            <span className="text-blue-500">{selectedConv.annotation_count} 注釈</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
                    {/* User filter for this conversation */}
                    {conversationUsers.length > 1 && (
                      <Select value={selectedUserFilter || "all"} onValueChange={v => setSelectedUserFilter(v === "all" ? "" : v)}>
                        <SelectTrigger className="h-7 w-24 sm:w-36 text-[11px]">
                          <User className="w-3 h-3 mr-1" />
                          <SelectValue placeholder="ユーザー" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">全ユーザー</SelectItem>
                          {conversationUsers.map(u => (
                            <SelectItem key={u} value={u}>{u.split("@")[0]}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                    <a
                      href={`/marketing-v2/${selectedConvId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-[var(--brand-400)] hover:text-[var(--brand-300)] transition-colors"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span className="hidden sm:inline">会話を開く</span>
                    </a>
                  </div>
                </div>
              </div>

              {/* Detail Content */}
              <div className="flex-1 overflow-y-auto custom-scrollbar px-3 sm:px-5 py-3 sm:py-4 space-y-4">
                {detailLoading && (
                  <div className="flex items-center justify-center h-20 text-[12px] text-muted-foreground">読み込み中...</div>
                )}
                {conversationDetail && !detailLoading && (
                  <ConversationDetailView
                    feedback={conversationDetail.feedback}
                    annotations={conversationDetail.annotations}
                    onUpdateReview={async (id, status, notes) => {
                      const ok = await updateReview(id, status, notes);
                      if (ok) {
                        loadConversationDetail(selectedConvId!, selectedUserFilter || undefined);
                        loadOverview();
                        loadConversations({ page: convPage, rating: ratingFilter, user_email: userFilter });
                      }
                      return ok;
                    }}
                  />
                )}
                {conversationDetail && !detailLoading &&
                  conversationDetail.feedback.length === 0 &&
                  conversationDetail.annotations.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-32 text-muted-foreground/50">
                    <MessageSquare className="w-5 h-5 mb-2" />
                    <p className="text-[12px]">
                      {selectedUserFilter ? "このユーザーのFBはありません" : "この会話にはFBがありません"}
                    </p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════
// KPI Card
// ════════════════════════════════════════════════════════════

function KPICard({ icon: Icon, label, value, sub, color }: {
  icon: typeof MessageSquare;
  label: string;
  value: number;
  sub?: string;
  color?: "emerald" | "red" | "amber";
}) {
  const colors = {
    emerald: { icon: "text-emerald-500", value: "text-emerald-600", bg: "bg-emerald-50/50" },
    red:     { icon: "text-red-500", value: "text-red-500", bg: "bg-red-50/50" },
    amber:   { icon: "text-amber-500", value: "text-amber-600", bg: "bg-amber-50/50" },
  };
  const c = color ? colors[color] : { icon: "text-slate-400", value: "text-foreground", bg: "bg-slate-50/50" };

  return (
    <div className={`rounded-lg px-3.5 py-2.5 ${c.bg} border border-border/30`}>
      <div className="flex items-center gap-1.5 mb-0.5">
        <Icon className={`w-3.5 h-3.5 ${c.icon}`} />
        <span className="text-[10px] text-muted-foreground font-medium">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-xl font-bold tabular-nums ${c.value}`}>{value}</span>
        {sub && <span className="text-[10px] text-muted-foreground">{sub}</span>}
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════
// Conversation Card (left panel item)
// ════════════════════════════════════════════════════════════

function ConversationCard({ conv, isSelected, onClick }: {
  conv: ConversationFeedbackSummary;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(); } }}
      className={`
        px-3.5 py-3 border-b border-border/20 cursor-pointer transition-all duration-150
        ${isSelected
          ? "bg-[var(--brand-100)]/15 border-l-2 border-l-[var(--brand-400)]"
          : "hover:bg-slate-50/80 border-l-2 border-l-transparent"
        }
      `}
    >
      {/* Title row */}
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <h3 className={`text-[12px] font-medium leading-snug line-clamp-2 ${isSelected ? "text-[var(--brand-400)]" : ""}`}>
          {conv.title || "無題の会話"}
        </h3>
        {conv.unreviewed_count > 0 && (
          <span className="shrink-0 w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold flex items-center justify-center">
            {conv.unreviewed_count}
          </span>
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-2 text-[10px]">
        {conv.good_count > 0 && (
          <span className="inline-flex items-center gap-0.5 text-emerald-600">
            <ThumbsUp className="w-2.5 h-2.5" /> {conv.good_count}
          </span>
        )}
        {conv.bad_count > 0 && (
          <span className="inline-flex items-center gap-0.5 text-red-500">
            <ThumbsDown className="w-2.5 h-2.5" /> {conv.bad_count}
          </span>
        )}
        {conv.annotation_count > 0 && (
          <span className="inline-flex items-center gap-0.5 text-blue-500">
            <Pencil className="w-2.5 h-2.5" /> {conv.annotation_count}
          </span>
        )}
        <span className="inline-flex items-center gap-0.5 text-muted-foreground/50">
          <Users className="w-2.5 h-2.5" /> {conv.unique_users}
        </span>
      </div>

      {/* Meta row */}
      <div className="flex items-center justify-between mt-1.5 text-[10px] text-muted-foreground/50">
        <span>{conv.owner_email?.split("@")[0]}</span>
        <span>
          {conv.latest_feedback_at
            ? new Date(conv.latest_feedback_at).toLocaleDateString("ja-JP", { month: "numeric", day: "numeric" })
            : ""}
        </span>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════
// Conversation Detail View (right panel)
// ════════════════════════════════════════════════════════════

function ConversationDetailView({ feedback, annotations, onUpdateReview }: {
  feedback: MessageFeedback[];
  annotations: MessageAnnotation[];
  onUpdateReview: (id: string, status: ReviewStatus, notes?: string) => Promise<boolean>;
}) {
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");

  const handleReview = async (id: string, status: ReviewStatus) => {
    const ok = await onUpdateReview(id, status, reviewNotes || undefined);
    if (ok) {
      setReviewingId(null);
      setReviewNotes("");
    }
  };

  return (
    <div className="space-y-5">
      {/* ── Feedback Section ── */}
      {feedback.length > 0 && (
        <section>
          <h3 className="text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-widest mb-2.5 flex items-center gap-1.5">
            <ThumbsUp className="w-3 h-3" />
            メッセージ評価 ({feedback.length})
          </h3>
          <div className="space-y-2">
            {feedback.map(fb => (
              <div
                key={fb.id}
                className={`
                  rounded-lg border border-border/40 bg-white p-3.5 transition-all
                  ${fb.review_status === "new" ? "border-l-2 border-l-amber-400" : ""}
                `}
              >
                {/* Header: rating + status + user */}
                <div className="flex flex-wrap items-center justify-between gap-1.5 mb-2">
                  <div className="flex items-center gap-2">
                    {fb.rating === "good" ? (
                      <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center">
                        <ThumbsUp className="w-2.5 h-2.5 text-emerald-600" />
                      </div>
                    ) : fb.rating === "bad" ? (
                      <div className="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center">
                        <ThumbsDown className="w-2.5 h-2.5 text-red-500" />
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center">
                        <MessageSquare className="w-2.5 h-2.5 text-slate-400" />
                      </div>
                    )}
                    <span className="text-[11px] font-medium">
                      {fb.rating === "good" ? "Good" : fb.rating === "bad" ? "Bad" : "評価なし"}
                    </span>
                    <StatusBadge status={fb.review_status} />
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground/50">
                    <span>{fb.user_email?.split("@")[0]}</span>
                    <span className="hidden sm:inline">
                      {new Date(fb.created_at).toLocaleDateString("ja-JP", { month: "numeric", day: "numeric" })}
                      {" "}
                      {new Date(fb.created_at).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                </div>

                {/* Tags */}
                {fb.tags && fb.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {fb.tags.map(t => (
                      <span key={t} className="inline-flex text-[9px] font-medium bg-slate-100 text-slate-600 rounded px-1.5 py-0.5">
                        {t}
                      </span>
                    ))}
                  </div>
                )}

                {/* Comment */}
                {fb.comment && (
                  <p className="text-[12px] text-slate-600 leading-relaxed mb-2 pl-2 border-l-2 border-slate-200">
                    {fb.comment}
                  </p>
                )}

                {/* Correction */}
                {fb.correction && (
                  <div className="text-[11px] text-emerald-700 bg-emerald-50/80 rounded px-2.5 py-1.5 border border-emerald-100 mb-2">
                    <span className="font-medium">修正案: </span>{fb.correction}
                  </div>
                )}

                {/* Review actions */}
                {reviewingId === fb.id ? (
                  <div className="mt-2 space-y-2 pt-2 border-t border-border/30">
                    <Textarea
                      placeholder="レビューメモ（任意）"
                      value={reviewNotes}
                      onChange={e => setReviewNotes(e.target.value)}
                      className="text-[11px] min-h-[50px] resize-none"
                    />
                    <div className="flex flex-wrap gap-1.5">
                      <Button size="sm" variant="outline" className="h-7 sm:h-6 text-[10px] gap-1" onClick={() => handleReview(fb.id, "reviewed")}>
                        <Eye className="w-2.5 h-2.5" /> レビュー済
                      </Button>
                      <Button size="sm" className="h-7 sm:h-6 text-[10px] gap-1 bg-emerald-600 hover:bg-emerald-700" onClick={() => handleReview(fb.id, "actioned")}>
                        <CheckCircle2 className="w-2.5 h-2.5" /> 対応済
                      </Button>
                      <Button size="sm" variant="outline" className="h-7 sm:h-6 text-[10px] gap-1 text-muted-foreground" onClick={() => handleReview(fb.id, "dismissed")}>
                        <XCircle className="w-2.5 h-2.5" /> 却下
                      </Button>
                      <Button size="sm" variant="ghost" className="h-7 sm:h-6 text-[10px] ml-auto" onClick={() => { setReviewingId(null); setReviewNotes(""); }}>
                        キャンセル
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-between mt-1">
                    {fb.reviewed_by && (
                      <span className="text-[9px] text-muted-foreground/40">
                        レビュー: {fb.reviewed_by?.split("@")[0]}
                      </span>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-5 text-[10px] text-muted-foreground/50 hover:text-foreground ml-auto px-1.5"
                      onClick={() => { setReviewingId(fb.id); setReviewNotes(""); }}
                    >
                      レビュー
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Annotations Section ── */}
      {annotations.length > 0 && (
        <section>
          <h3 className="text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-widest mb-2.5 flex items-center gap-1.5">
            <Pencil className="w-3 h-3" />
            テキストアノテーション ({annotations.length})
          </h3>
          <div className="space-y-2">
            {annotations.map(ann => {
              const sev = SEV[ann.severity] || SEV.info;
              const sel = ann.selector as { type: string; quote?: { exact?: string } };

              return (
                <div
                  key={ann.id}
                  className={`
                    rounded-lg border border-border/40 bg-white p-3.5 border-l-[3px] transition-all
                    ${ann.review_status === "new" ? "border-l-amber-400" : `border-l-${sev.dot.replace("bg-", "")}`}
                  `}
                  style={{
                    borderLeftColor: ann.review_status === "new"
                      ? undefined
                      : sev.dot === "bg-red-500" ? "#ef4444"
                      : sev.dot === "bg-orange-500" ? "#f97316"
                      : sev.dot === "bg-amber-400" ? "#fbbf24"
                      : sev.dot === "bg-blue-500" ? "#3b82f6"
                      : sev.dot === "bg-emerald-500" ? "#10b981"
                      : undefined
                  }}
                >
                  {/* Header */}
                  <div className="flex flex-wrap items-center justify-between gap-1 mb-1.5">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className={`inline-flex text-[10px] font-semibold rounded px-1.5 py-0.5 leading-none ${sev.bg} ${sev.text}`}>
                        {sev.label}
                      </span>
                      {ann.tags.slice(0, 3).map(t => (
                        <span key={t} className="text-[9px] font-medium text-muted-foreground bg-slate-100 rounded px-1.5 py-0.5 leading-none">
                          {t}
                        </span>
                      ))}
                      <StatusBadge status={ann.review_status} />
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground/50">
                      <span>{ann.user_email?.split("@")[0]}</span>
                      <span className="hidden sm:inline">
                        {new Date(ann.created_at).toLocaleDateString("ja-JP", { month: "numeric", day: "numeric" })}
                      </span>
                    </div>
                  </div>

                  {/* Quote */}
                  {sel.quote?.exact && (
                    <p className="text-[11px] text-slate-500 leading-relaxed line-clamp-3 pl-2 border-l border-slate-200 mb-1.5">
                      {sel.quote.exact.slice(0, 120)}{sel.quote.exact.length > 120 ? "..." : ""}
                    </p>
                  )}

                  {/* Comment */}
                  {ann.comment && (
                    <p className="text-[12px] text-slate-700 leading-relaxed mb-1.5">
                      {ann.comment}
                    </p>
                  )}

                  {/* Correction */}
                  {ann.correction && (
                    <div className="text-[10px] text-emerald-700 bg-emerald-50/80 rounded px-2 py-1 border border-emerald-100 mb-1.5">
                      <span className="font-medium">修正案:</span> {ann.correction}
                    </div>
                  )}

                  {/* Review */}
                  {reviewingId === ann.id ? (
                    <div className="mt-2 space-y-2 pt-2 border-t border-border/30">
                      <Textarea
                        placeholder="レビューメモ（任意）"
                        value={reviewNotes}
                        onChange={e => setReviewNotes(e.target.value)}
                        className="text-[11px] min-h-[50px] resize-none"
                      />
                      <div className="flex gap-1.5">
                        <Button size="sm" variant="outline" className="h-6 text-[10px] gap-1" onClick={() => handleReview(ann.id, "reviewed")}>
                          <Eye className="w-2.5 h-2.5" /> レビュー済
                        </Button>
                        <Button size="sm" className="h-6 text-[10px] gap-1 bg-emerald-600 hover:bg-emerald-700" onClick={() => handleReview(ann.id, "actioned")}>
                          <CheckCircle2 className="w-2.5 h-2.5" /> 対応済
                        </Button>
                        <Button size="sm" variant="outline" className="h-6 text-[10px] gap-1 text-muted-foreground" onClick={() => handleReview(ann.id, "dismissed")}>
                          <XCircle className="w-2.5 h-2.5" /> 却下
                        </Button>
                        <Button size="sm" variant="ghost" className="h-6 text-[10px] ml-auto" onClick={() => { setReviewingId(null); setReviewNotes(""); }}>
                          キャンセル
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between mt-1">
                      {ann.reviewed_by && (
                        <span className="text-[9px] text-muted-foreground/40">
                          レビュー: {ann.reviewed_by?.split("@")[0]}
                        </span>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-5 text-[10px] text-muted-foreground/50 hover:text-foreground ml-auto px-1.5"
                        onClick={() => { setReviewingId(ann.id); setReviewNotes(""); }}
                      >
                        レビュー
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
