"use client";

/**
 * Feedback Review Dashboard
 *
 * Admin page for reviewing, analyzing, and exporting agent feedback.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ThumbsUp,
  ThumbsDown,
  Eye,
  Download,
  Filter,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
  MessageSquare,
  TrendingUp,
  BarChart3,
  X,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { useFeedbackDashboard } from "@/hooks/use-feedback";
import type { MessageFeedback, ReviewStatus } from "@/lib/feedback/types";

// Token management (same pattern as marketing-v2)
type TokenState = { secret: string | null; expiresAt: number };

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
    listData,
    loading,
    tags,
    loadOverview,
    loadList,
    updateReview,
    exportFeedback,
  } = useFeedbackDashboard(getClientSecret);

  // Filters
  const [ratingFilter, setRatingFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [tagFilter, setTagFilter] = useState<string>("");
  const [page, setPage] = useState(1);

  // Detail sheet
  const [selectedItem, setSelectedItem] = useState<MessageFeedback | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");

  // Initial load
  useEffect(() => {
    (async () => {
      await ensureClientSecret();
      loadOverview();
      loadList({ page: 1 });
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Reload list when filters change
  useEffect(() => {
    if (!tokenRef.current.secret) return;
    loadList({
      page,
      rating: ratingFilter || undefined,
      review_status: statusFilter || undefined,
      tag: tagFilter || undefined,
    });
  }, [page, ratingFilter, statusFilter, tagFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleUpdateReview = async (id: string, status: ReviewStatus) => {
    const ok = await updateReview(id, status, reviewNotes || undefined);
    if (ok) {
      loadList({ page, rating: ratingFilter, review_status: statusFilter, tag: tagFilter });
      loadOverview();
      setSelectedItem(null);
      setReviewNotes("");
    }
  };

  const handleExport = async (format: "jsonl" | "csv") => {
    await ensureClientSecret();
    await exportFeedback(format, {
      rating: ratingFilter || undefined,
      review_status: statusFilter || undefined,
      tag: tagFilter || undefined,
    });
  };

  const statusBadge = (s: string) => {
    switch (s) {
      case "new": return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">新規</Badge>;
      case "reviewed": return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">レビュー済</Badge>;
      case "actioned": return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">対応済</Badge>;
      case "dismissed": return <Badge variant="outline" className="bg-gray-50 text-gray-500 border-gray-200">却下</Badge>;
      default: return <Badge variant="outline">{s}</Badge>;
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-background">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Feedback Review</h1>
            <p className="text-sm text-muted-foreground">b&q エージェントのフィードバック分析・レビュー</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => handleExport("csv")}>
              <Download className="w-3.5 h-3.5 mr-1.5" />
              CSV
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleExport("jsonl")}>
              <Download className="w-3.5 h-3.5 mr-1.5" />
              JSONL
            </Button>
          </div>
        </div>

        {/* KPI Cards */}
        {overview && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <KPICard icon={MessageSquare} label="Total FB" value={overview.total} />
            <KPICard icon={ThumbsUp} label="Good" value={overview.good} sub={`${overview.good_pct}%`} color="text-emerald-600" />
            <KPICard icon={ThumbsDown} label="Bad" value={overview.bad} sub={`${overview.bad_pct}%`} color="text-red-500" />
            <KPICard icon={Clock} label="未レビュー" value={overview.unreviewed} color="text-amber-600" />
          </div>
        )}

        {/* Charts */}
        {overview && overview.trend.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Trend Chart */}
            <div className="border rounded-lg p-4">
              <h3 className="text-sm font-medium mb-3 flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4" /> 日別トレンド
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={[...overview.trend].reverse()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} tickFormatter={v => v.slice(5)} />
                  <YAxis tick={{ fontSize: 11 }} width={30} />
                  <Tooltip />
                  <Area type="monotone" dataKey="good" stackId="1" fill="#86efac" stroke="#22c55e" name="Good" />
                  <Area type="monotone" dataKey="bad" stackId="1" fill="#fca5a5" stroke="#ef4444" name="Bad" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Tag Chart */}
            <div className="border rounded-lg p-4">
              <h3 className="text-sm font-medium mb-3 flex items-center gap-1.5">
                <BarChart3 className="w-4 h-4" /> タグ別問題頻度
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={overview.top_tags.slice(0, 8)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="tag" type="category" tick={{ fontSize: 11 }} width={100} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#f97316" radius={[0, 4, 4, 0]} name="件数" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 p-3 border rounded-lg bg-muted/30">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <Select value={ratingFilter} onValueChange={v => { setRatingFilter(v === "all" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-28 h-8 text-xs"><SelectValue placeholder="評価" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全て</SelectItem>
              <SelectItem value="good">Good</SelectItem>
              <SelectItem value="bad">Bad</SelectItem>
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={v => { setStatusFilter(v === "all" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-32 h-8 text-xs"><SelectValue placeholder="ステータス" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全て</SelectItem>
              <SelectItem value="new">新規</SelectItem>
              <SelectItem value="reviewed">レビュー済</SelectItem>
              <SelectItem value="actioned">対応済</SelectItem>
              <SelectItem value="dismissed">却下</SelectItem>
            </SelectContent>
          </Select>
          <Select value={tagFilter} onValueChange={v => { setTagFilter(v === "all" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-40 h-8 text-xs"><SelectValue placeholder="タグ" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全て</SelectItem>
              {tags.map(t => (
                <SelectItem key={t.key} value={t.key}>{t.display_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Feedback List */}
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 border-b">
                <th className="text-left px-4 py-2.5 font-medium w-12">評価</th>
                <th className="text-left px-4 py-2.5 font-medium">日時</th>
                <th className="text-left px-4 py-2.5 font-medium">ユーザー</th>
                <th className="text-left px-4 py-2.5 font-medium">メッセージ</th>
                <th className="text-left px-4 py-2.5 font-medium">タグ</th>
                <th className="text-left px-4 py-2.5 font-medium">ステータス</th>
                <th className="text-right px-4 py-2.5 font-medium w-16">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && !listData && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">読み込み中...</td></tr>
              )}
              {listData && listData.items.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">フィードバックがありません</td></tr>
              )}
              {listData?.items.map(item => (
                <tr key={item.id} className="border-b hover:bg-muted/20 transition-colors">
                  <td className="px-4 py-2.5">
                    {item.rating === "good" ? (
                      <ThumbsUp className="w-4 h-4 text-emerald-500" />
                    ) : item.rating === "bad" ? (
                      <ThumbsDown className="w-4 h-4 text-red-500" />
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(item.created_at).toLocaleDateString("ja-JP", { month: "2-digit", day: "2-digit" })}
                    {" "}
                    {new Date(item.created_at).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="px-4 py-2.5 text-xs truncate max-w-[100px]">
                    {item.user_email?.split("@")[0]}
                  </td>
                  <td className="px-4 py-2.5 text-xs truncate max-w-[200px]">
                    {item.marketing_messages?.plain_text?.slice(0, 60) || "-"}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex gap-1 flex-wrap">
                      {(item.tags || []).slice(0, 2).map(t => (
                        <Badge key={t} variant="outline" className="text-[10px] px-1.5 py-0">{t}</Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">{statusBadge(item.review_status)}</td>
                  <td className="px-4 py-2.5 text-right">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setSelectedItem(item); setReviewNotes(""); }}>
                      <Eye className="w-3.5 h-3.5" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {listData && listData.total_pages > 1 && (
            <div className="flex items-center justify-between px-4 py-2.5 border-t bg-muted/30">
              <span className="text-xs text-muted-foreground">
                {listData.total}件中 {(page - 1) * listData.per_page + 1}-{Math.min(page * listData.per_page, listData.total)}件
              </span>
              <div className="flex gap-1">
                <Button variant="outline" size="icon" className="h-7 w-7" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                  <ChevronLeft className="w-3.5 h-3.5" />
                </Button>
                <span className="text-xs px-2 flex items-center">{page}/{listData.total_pages}</span>
                <Button variant="outline" size="icon" className="h-7 w-7" disabled={page >= listData.total_pages} onClick={() => setPage(p => p + 1)}>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Detail Sheet */}
      <Sheet open={!!selectedItem} onOpenChange={(open) => { if (!open) setSelectedItem(null); }}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          {selectedItem && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  {selectedItem.rating === "good" ? <ThumbsUp className="w-4 h-4 text-emerald-500" /> : <ThumbsDown className="w-4 h-4 text-red-500" />}
                  フィードバック詳細
                </SheetTitle>
              </SheetHeader>

              <div className="mt-4 space-y-4">
                {/* Conversation link */}
                <div>
                  <a
                    href={`/marketing-v2/${selectedItem.conversation_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    会話を開く ({selectedItem.marketing_conversations?.title || selectedItem.conversation_id?.slice(0, 8)})
                  </a>
                </div>

                {/* Message preview */}
                <div className="border rounded-lg p-3 bg-muted/30">
                  <label className="text-xs font-medium text-muted-foreground block mb-1">対象メッセージ</label>
                  <p className="text-sm whitespace-pre-wrap">{selectedItem.marketing_messages?.plain_text?.slice(0, 500) || "N/A"}</p>
                </div>

                {/* Rating & Tags */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium w-16">評価:</span>
                    {selectedItem.rating === "good" ? (
                      <Badge className="bg-emerald-100 text-emerald-700">Good</Badge>
                    ) : (
                      <Badge className="bg-red-100 text-red-700">Bad</Badge>
                    )}
                  </div>
                  {selectedItem.tags && selectedItem.tags.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium w-16">タグ:</span>
                      <div className="flex gap-1 flex-wrap">
                        {selectedItem.tags.map(t => (
                          <Badge key={t} variant="outline">{t}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Comment */}
                {selectedItem.comment && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1">コメント</label>
                    <p className="text-sm p-2 border rounded bg-white">{selectedItem.comment}</p>
                  </div>
                )}

                {/* Correction */}
                {selectedItem.correction && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1">修正案</label>
                    <p className="text-sm p-2 border rounded bg-amber-50">{selectedItem.correction}</p>
                  </div>
                )}

                {/* Dimension Scores */}
                {selectedItem.dimension_scores && Object.keys(selectedItem.dimension_scores).length > 0 && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1">多次元評価</label>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(selectedItem.dimension_scores).map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between text-sm border rounded px-2 py-1">
                          <span>{key}</span>
                          <span className="font-medium">{String(val)}/5</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Meta */}
                <div className="text-xs text-muted-foreground space-y-0.5">
                  <div>投稿者: {selectedItem.user_email}</div>
                  <div>投稿日: {new Date(selectedItem.created_at).toLocaleString("ja-JP")}</div>
                  {selectedItem.reviewed_by && <div>レビュー者: {selectedItem.reviewed_by}</div>}
                </div>

                {/* Review Actions */}
                <div className="border-t pt-4 space-y-3">
                  <label className="text-xs font-medium block">レビュー</label>
                  <div className="flex items-center gap-2">
                    <span className="text-xs w-20">現在のステータス:</span>
                    {statusBadge(selectedItem.review_status)}
                  </div>
                  <Textarea
                    placeholder="レビューメモ（任意）"
                    value={reviewNotes}
                    onChange={e => setReviewNotes(e.target.value)}
                    className="text-sm min-h-[60px] resize-none"
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1.5"
                      onClick={() => handleUpdateReview(selectedItem.id, "reviewed")}
                    >
                      <Eye className="w-3.5 h-3.5" />
                      レビュー済み
                    </Button>
                    <Button
                      size="sm"
                      className="gap-1.5 bg-emerald-600 hover:bg-emerald-700"
                      onClick={() => handleUpdateReview(selectedItem.id, "actioned")}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      対応済み
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1.5 text-muted-foreground"
                      onClick={() => handleUpdateReview(selectedItem.id, "dismissed")}
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      却下
                    </Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

// KPI Card
function KPICard({ icon: Icon, label, value, sub, color }: {
  icon: typeof MessageSquare;
  label: string;
  value: number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`w-4 h-4 ${color || "text-muted-foreground"}`} />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className={`text-2xl font-semibold ${color || ""}`}>{value}</span>
        {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
      </div>
    </div>
  );
}
