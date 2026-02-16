"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowUpDown,
  Calendar,
  ChevronRight,
  Clock,
  FileText,
  Loader2,
  RefreshCw,
  Search,
  UserCheck,
  Users,
  X,
} from "lucide-react";

import { apiClient, type CandidateListResponse, type CandidateSummary } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SidebarTrigger } from "@/components/ui/sidebar";

const PAGE_SIZE = 20;

// ステータスに応じたBadge variant
function getStatusVariant(status: string | null): "default" | "secondary" | "destructive" | "outline" {
  if (!status) return "secondary";
  const num = parseInt(status);
  if (num >= 12 && num <= 14) return "default"; // 内定〜入社
  if (num >= 15 && num <= 17) return "destructive"; // 退職・クローズ・連絡禁止
  return "secondary";
}

// ステータスの短縮表示
function getStatusLabel(status: string | null): string {
  if (!status) return "不明";
  // "1. リード" → "リード"
  const match = status.match(/^\d+\.\s*(.+)/);
  return match ? match[1] : status;
}

// チャネルの表示名
function getChannelLabel(channel: string | null): string {
  if (!channel) return "";
  const labels: Record<string, string> = {
    sco_bizreach: "BizReach",
    sco_dodaX: "dodaX",
    sco_ambi: "Ambi",
    sco_rikunavi: "リクナビ",
    sco_nikkei: "日経",
    sco_liiga: "Liiga",
    sco_openwork: "OpenWork",
    sco_carinar: "Carinar",
    "sco_dodaX_D&P": "dodaX D&P",
    paid_google: "Google Ads",
    paid_meta: "Meta Ads",
    paid_affiliate: "Affiliate",
    org_hitocareer: "hitocareer",
    org_jobs: "Jobs",
    feed_indeed: "Indeed",
    referral: "紹介",
    other: "その他",
  };
  return labels[channel] || channel;
}

export default function CandidatesPage() {
  const searchParams = useSearchParams();

  // URL params から初期値を読み取り
  const initialPage = parseInt(searchParams.get("page") || "1");
  const initialStatus = searchParams.get("status") || "";
  const initialChannel = searchParams.get("channel") || "";
  const initialSort = searchParams.get("sort") || "registration_date";
  const initialSearch = searchParams.get("search") || "";

  const [response, setResponse] = useState<CandidateListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(initialPage);
  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [debouncedSearch, setDebouncedSearch] = useState(initialSearch);
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [channelFilter, setChannelFilter] = useState(initialChannel);
  const [sortBy, setSortBy] = useState(initialSort);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // デバウンス検索
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery]);

  // URL状態保持
  const updateUrl = useCallback(() => {
    const params = new URLSearchParams();
    if (page > 1) params.set("page", page.toString());
    if (statusFilter) params.set("status", statusFilter);
    if (channelFilter) params.set("channel", channelFilter);
    if (sortBy !== "registration_date") params.set("sort", sortBy);
    if (debouncedSearch) params.set("search", debouncedSearch);
    const qs = params.toString();
    const newUrl = `/hitocari/candidates${qs ? `?${qs}` : ""}`;
    window.history.replaceState(null, "", newUrl);
  }, [page, statusFilter, channelFilter, sortBy, debouncedSearch]);

  useEffect(() => {
    updateUrl();
  }, [updateUrl]);

  // データ取得
  const loadCandidates = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiClient.getCandidates(
        page,
        PAGE_SIZE,
        debouncedSearch || undefined,
        statusFilter || undefined,
        channelFilter || undefined,
        sortBy,
      );
      setResponse(result);
    } catch (err) {
      console.error("Failed to load candidates:", err);
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, statusFilter, channelFilter, sortBy]);

  useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

  // フィルタ変更時にページリセット
  const handleStatusChange = (value: string) => {
    setStatusFilter(value === "__all__" ? "" : value);
    setPage(1);
  };

  const handleChannelChange = (value: string) => {
    setChannelFilter(value === "__all__" ? "" : value);
    setPage(1);
  };

  const handleSortChange = (value: string) => {
    setSortBy(value);
    setPage(1);
  };

  const clearFilters = () => {
    setSearchQuery("");
    setDebouncedSearch("");
    setStatusFilter("");
    setChannelFilter("");
    setSortBy("registration_date");
    setPage(1);
  };

  const hasActiveFilters = statusFilter || channelFilter || debouncedSearch || sortBy !== "registration_date";

  // フィルタオプション
  const statuses = useMemo(() => response?.filters?.statuses || [], [response]);
  const channels = useMemo(() => response?.filters?.channels || [], [response]);

  const sortOptions = [
    { value: "registration_date", label: "登録日（新しい順）" },
    { value: "modified_time", label: "最終更新（新しい順）" },
    { value: "created_time", label: "作成日（新しい順）" },
    { value: "status", label: "ステータス順" },
  ];

  return (
    <div className="w-full px-3 py-4 sm:px-6 sm:py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3 min-w-0">
          <SidebarTrigger className="md:hidden" />
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-2">
              <UserCheck className="h-6 w-6 sm:h-7 sm:w-7 shrink-0" />
              候補者管理
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Zoho CRM の候補者情報を一覧管理
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadCandidates}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">更新</span>
        </Button>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-4 sm:p-6">
          <div className="space-y-3">
            {/* Search + Sort */}
            <div className="flex flex-col space-y-2 sm:flex-row sm:space-y-0 sm:space-x-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="候補者名で検索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Select value={sortBy} onValueChange={handleSortChange}>
                <SelectTrigger className="w-full sm:w-[160px]">
                  <ArrowUpDown className="h-4 w-4 mr-2 shrink-0" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {sortOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Status + Channel filters */}
            <div className="flex flex-col space-y-2 sm:flex-row sm:space-y-0 sm:space-x-3">
              <Select value={statusFilter || "__all__"} onValueChange={handleStatusChange}>
                <SelectTrigger className="w-full sm:w-[220px]">
                  <SelectValue placeholder="ステータス" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">全ステータス</SelectItem>
                  {statuses.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={channelFilter || "__all__"} onValueChange={handleChannelChange}>
                <SelectTrigger className="w-full sm:w-[180px]">
                  <SelectValue placeholder="チャネル" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">全チャネル</SelectItem>
                  {channels.map((ch) => (
                    <SelectItem key={ch} value={ch}>
                      {getChannelLabel(ch)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {hasActiveFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters} className="self-start">
                  <X className="h-4 w-4 mr-1" />
                  クリア
                </Button>
              )}
            </div>

            {/* Results count */}
            {response && (
              <div className="text-xs sm:text-sm text-muted-foreground">
                {response.total}件の候補者
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">読み込み中...</p>
          </div>
        </div>
      ) : !response || response.items.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Users className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium text-muted-foreground mb-2">
              候補者が見つかりません
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              {hasActiveFilters
                ? "フィルタ条件を変更してお試しください"
                : "Zoho CRMに候補者データが登録されていません"}
            </p>
            {hasActiveFilters && (
              <Button variant="outline" onClick={clearFilters}>
                フィルタをクリア
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2 sm:space-y-3">
          {response.items.map((candidate) => (
            <CandidateCard key={candidate.record_id} candidate={candidate} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {response && response.total_pages > 1 && (
        <PaginationControls
          page={page}
          totalPages={response.total_pages}
          hasNext={response.has_next}
          hasPrevious={response.has_previous}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}

function CandidateCard({ candidate }: { candidate: CandidateSummary }) {
  return (
    <Link href={`/hitocari/candidates/${candidate.record_id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer active:scale-[0.98]">
        <CardContent className="p-4 sm:p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0 space-y-2">
              {/* Name + Badges */}
              <div className="flex flex-col space-y-2 sm:flex-row sm:items-center sm:space-y-0 sm:space-x-2">
                <h3 className="text-base sm:text-lg font-medium line-clamp-1 min-w-0">
                  {candidate.name || "名前未設定"}
                </h3>
                <div className="flex items-center space-x-1 shrink-0 flex-wrap gap-1">
                  <Badge variant={getStatusVariant(candidate.status)}>
                    {getStatusLabel(candidate.status)}
                  </Badge>
                  {candidate.channel && (
                    <Badge variant="outline" className="text-xs">
                      {getChannelLabel(candidate.channel)}
                    </Badge>
                  )}
                </div>
              </div>

              {/* Metadata */}
              <div className="space-y-1 sm:space-y-0 sm:flex sm:items-center sm:space-x-4 text-xs sm:text-sm text-muted-foreground">
                {candidate.pic && (
                  <div className="flex items-center space-x-1">
                    <UserCheck className="h-3 w-3 sm:h-4 sm:w-4 shrink-0" />
                    <span className="truncate max-w-[120px]">{candidate.pic}</span>
                  </div>
                )}
                {candidate.registration_date && (
                  <div className="flex items-center space-x-1 shrink-0">
                    <Calendar className="h-3 w-3 sm:h-4 sm:w-4" />
                    <span>登録 {candidate.registration_date}</span>
                  </div>
                )}
                {candidate.modified_time && (
                  <div className="flex items-center space-x-1 shrink-0">
                    <Clock className="h-3 w-3 sm:h-4 sm:w-4" />
                    <span>更新 {candidate.modified_time.split("T")[0]}</span>
                  </div>
                )}
                {candidate.linked_meetings_count > 0 && (
                  <div className="flex items-center space-x-1 shrink-0">
                    <FileText className="h-3 w-3 sm:h-4 sm:w-4" />
                    <span>議事録 {candidate.linked_meetings_count}件</span>
                  </div>
                )}
              </div>
            </div>

            <ChevronRight className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground ml-2 sm:ml-4 shrink-0 mt-1" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

function PaginationControls({
  page,
  totalPages,
  hasNext,
  hasPrevious,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onPageChange: (p: number) => void;
}) {
  const pageNumbers = useMemo(() => {
    const pages: number[] = [];
    const start = Math.max(1, Math.min(totalPages - 2, page - 1));
    for (let i = start; i <= Math.min(start + 2, totalPages); i++) {
      pages.push(i);
    }
    return pages;
  }, [page, totalPages]);

  return (
    <div className="flex flex-col space-y-3 sm:flex-row sm:items-center sm:justify-between mt-6">
      <div className="text-xs sm:text-sm text-muted-foreground text-center sm:text-left">
        ページ {page} / {totalPages}
      </div>
      <div className="flex items-center justify-center space-x-1 sm:space-x-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={!hasPrevious}
        >
          前へ
        </Button>
        {pageNumbers.map((num) => (
          <Button
            key={num}
            variant={num === page ? "default" : "outline"}
            size="sm"
            onClick={() => onPageChange(num)}
          >
            {num}
          </Button>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={!hasNext}
        >
          次へ
        </Button>
      </div>
    </div>
  );
}
