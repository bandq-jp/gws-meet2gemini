"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  Briefcase,
  Calendar,
  ExternalLink,
  FileText,
  Loader2,
  MapPin,
  Sparkles,
  UserCheck,
  Wallet,
} from "lucide-react";

import {
  apiClient,
  type CandidateDetail,
  type JobMatch,
  type JobMatchResult,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SidebarTrigger } from "@/components/ui/sidebar";

// ステータスに応じたBadge variant
function getStatusVariant(status: string | null | undefined): "default" | "secondary" | "destructive" | "outline" {
  if (!status) return "secondary";
  const s = String(status);
  const num = parseInt(s);
  if (num >= 12 && num <= 14) return "default";
  if (num >= 15 && num <= 17) return "destructive";
  return "secondary";
}

function getStatusLabel(status: string | null | undefined): string {
  if (!status) return "不明";
  const s = String(status);
  const match = s.match(/^\d+\.\s*(.+)/);
  return match ? match[1] : s;
}

function getChannelLabel(channel: string | null | undefined): string {
  if (!channel) return "";
  const labels: Record<string, string> = {
    sco_bizreach: "BizReach", sco_dodaX: "dodaX", sco_ambi: "Ambi",
    sco_rikunavi: "リクナビ", sco_nikkei: "日経", sco_liiga: "Liiga",
    sco_openwork: "OpenWork", sco_carinar: "Carinar", "sco_dodaX_D&P": "dodaX D&P",
    paid_google: "Google Ads", paid_meta: "Meta Ads", paid_affiliate: "Affiliate",
    org_hitocareer: "hitocareer", org_jobs: "Jobs", feed_indeed: "Indeed",
    referral: "紹介", other: "その他",
  };
  return labels[channel] || channel;
}

// Zohoフィールド定義
const BASIC_FIELDS = [
  { key: "Name", label: "求職者名" },
  { key: "field15", label: "年齢" },
  { key: "customer_status", label: "ステータス" },
  { key: "field14", label: "流入経路" },
  { key: "field18", label: "登録日" },
  { key: "field17", label: "現年収(万円)" },
  { key: "field20", label: "希望年収(万円)" },
  { key: "field66", label: "転職希望時期" },
  { key: "field85", label: "職歴" },
];

const OWNER_FIELD = { key: "Owner", label: "担当CA" };

// 構造化データの表示フィールド
const STRUCTURED_SECTIONS = [
  {
    title: "転職情報",
    fields: [
      { key: "transfer_reasons", label: "転職検討理由" },
      { key: "transfer_trigger", label: "きっかけ" },
      { key: "transfer_priorities", label: "転職軸" },
      { key: "desired_timing", label: "希望時期" },
      { key: "desired_industry", label: "希望業界" },
      { key: "desired_position", label: "希望職種" },
    ],
  },
  {
    title: "現職情報",
    fields: [
      { key: "current_company", label: "現職企業" },
      { key: "current_duties", label: "現職業務内容" },
      { key: "career_history", label: "職歴サマリー" },
      { key: "current_salary", label: "現年収" },
      { key: "desired_first_year_salary", label: "初年度希望年収" },
    ],
  },
  {
    title: "その他",
    fields: [
      { key: "personality_traits", label: "人物像" },
      { key: "strengths", label: "強み" },
      { key: "concerns", label: "懸念点" },
      { key: "next_steps", label: "ネクストステップ" },
    ],
  },
];

export default function CandidateDetailPage() {
  const params = useParams();
  const recordId = params.id as string;

  const [detail, setDetail] = useState<CandidateDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Job matching state
  const [matchResult, setMatchResult] = useState<JobMatchResult | null>(null);
  const [matching, setMatching] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    if (!recordId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.getCandidateDetail(recordId);
      setDetail(result);
    } catch (err) {
      console.error("Failed to load candidate detail:", err);
      setError("候補者情報の読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [recordId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleJobMatch = async () => {
    if (!recordId) return;
    setMatching(true);
    setMatchError(null);
    try {
      const result = await apiClient.matchCandidateJobs(recordId);
      setMatchResult(result);
    } catch (err) {
      console.error("Job matching failed:", err);
      setMatchError("マッチング分析に失敗しました。再度お試しください。");
    } finally {
      setMatching(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">候補者情報を読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="w-full px-3 py-4 sm:px-6 sm:py-6">
        <div className="flex items-center space-x-2 mb-6">
          <SidebarTrigger className="md:hidden" />
          <Link href="/hitocari/candidates">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              候補者一覧に戻る
            </Button>
          </Link>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <UserCheck className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium text-muted-foreground mb-2">
              {error || "候補者が見つかりません"}
            </h3>
          </CardContent>
        </Card>
      </div>
    );
  }

  const zoho = detail.zoho_record;
  const candidateName = (zoho.Name as string) || "名前未設定";
  const status = zoho.customer_status as string | undefined;
  const channel = zoho.field14 as string | undefined;
  const owner = zoho.Owner as Record<string, unknown> | string | undefined;
  const ownerName = typeof owner === "object" && owner ? (owner.name as string) : owner ? String(owner) : null;

  // 最新の構造化データ
  const latestStructured = detail.structured_outputs.length > 0 ? detail.structured_outputs[0] : null;

  return (
    <div className="w-full px-3 py-4 sm:px-6 sm:py-6">
      {/* Header */}
      <div className="flex items-center space-x-4 min-w-0 mb-6">
        <div className="flex items-center space-x-2 shrink-0">
          <SidebarTrigger className="md:hidden" />
          <Link href="/hitocari/candidates">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              一覧に戻る
            </Button>
          </Link>
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl sm:text-2xl font-bold truncate">{candidateName}</h1>
          <p className="text-sm text-muted-foreground truncate">候補者詳細</p>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid gap-6 xl:grid-cols-2">
        {/* Left Column: Candidate Info */}
        <div className="space-y-6 min-w-0">
          {/* Basic Info Card */}
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2 flex-wrap gap-1">
                    <Badge variant={getStatusVariant(status)}>
                      {getStatusLabel(status)}
                    </Badge>
                    {channel && (
                      <Badge variant="outline">{getChannelLabel(channel)}</Badge>
                    )}
                    {typeof zoho.id === "string" && zoho.id && (
                      <Button asChild variant="outline" size="sm">
                        <a
                          href={`https://crm.zoho.com/crm/org/tab/CustomModule1/${zoho.id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-4 w-4 mr-2" />
                          Zoho CRM
                        </a>
                      </Button>
                    )}
                  </div>
                  <CardTitle className="text-lg">{candidateName}</CardTitle>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 border border-border rounded-lg overflow-hidden">
                {BASIC_FIELDS.map((field, index) => {
                  const value = zoho[field.key];
                  return (
                    <div
                      key={field.key}
                      className={`flex flex-col sm:grid sm:grid-cols-[140px_1fr] lg:grid-cols-[180px_1fr] ${index > 0 ? "border-t border-border" : ""}`}
                    >
                      <div className="bg-muted/30 px-3 py-2 text-xs sm:text-sm font-medium text-muted-foreground sm:border-r border-border">
                        {field.label}
                      </div>
                      <div className="px-3 py-2 text-xs sm:text-sm border-t sm:border-t-0 border-border sm:border-0 min-w-0">
                        <RenderValue value={value} fieldKey={field.key} />
                      </div>
                    </div>
                  );
                })}
                {/* Owner field */}
                <div className="flex flex-col sm:grid sm:grid-cols-[140px_1fr] lg:grid-cols-[180px_1fr] border-t border-border">
                  <div className="bg-muted/30 px-3 py-2 text-xs sm:text-sm font-medium text-muted-foreground sm:border-r border-border">
                    {OWNER_FIELD.label}
                  </div>
                  <div className="px-3 py-2 text-xs sm:text-sm border-t sm:border-t-0 border-border sm:border-0 min-w-0">
                    {ownerName || <span className="text-muted-foreground">-</span>}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Structured Data Card */}
          {latestStructured && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <FileText className="h-5 w-5" />
                  面談抽出データ
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {STRUCTURED_SECTIONS.map((section) => {
                  const hasValues = section.fields.some(
                    (f) => latestStructured.data[f.key] !== undefined && latestStructured.data[f.key] !== null && latestStructured.data[f.key] !== ""
                  );
                  if (!hasValues) return null;
                  return (
                    <div key={section.title} className="space-y-2">
                      <h4 className="text-sm sm:text-base font-semibold">{section.title}</h4>
                      <div className="grid grid-cols-1 border border-border rounded-lg overflow-hidden">
                        {section.fields.map((field, index) => {
                          const value = latestStructured.data[field.key];
                          if (value === undefined || value === null || value === "") return null;
                          return (
                            <div
                              key={field.key}
                              className={`flex flex-col sm:grid sm:grid-cols-[140px_1fr] lg:grid-cols-[180px_1fr] ${index > 0 ? "border-t border-border" : ""}`}
                            >
                              <div className="bg-muted/30 px-3 py-2 text-xs sm:text-sm font-medium text-muted-foreground sm:border-r border-border">
                                {field.label}
                              </div>
                              <div className="px-3 py-2 text-xs sm:text-sm border-t sm:border-t-0 border-border sm:border-0 min-w-0">
                                <RenderStructuredValue value={value} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column: Meetings + Job Matching */}
        <div className="space-y-6 min-w-0">
          {/* Linked Meetings Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-5 w-5" />
                関連議事録 ({detail.linked_meetings.length}件)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {detail.linked_meetings.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  関連する議事録がありません
                </p>
              ) : (
                <div className="space-y-2">
                  {detail.linked_meetings.map((meeting) => (
                    <Link
                      key={meeting.meeting_id}
                      href={`/hitocari/${meeting.meeting_id}`}
                    >
                      <div className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors cursor-pointer">
                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium truncate">
                              {meeting.title || "タイトル不明"}
                            </span>
                            {meeting.is_structured && (
                              <Badge variant="default" className="text-xs shrink-0">
                                構造化済
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center space-x-3 text-xs text-muted-foreground">
                            {meeting.meeting_datetime && (
                              <div className="flex items-center space-x-1">
                                <Calendar className="h-3 w-3" />
                                <span>{meeting.meeting_datetime.split("T")[0]}</span>
                              </div>
                            )}
                            {meeting.organizer_email && (
                              <span className="truncate max-w-[150px]">{meeting.organizer_email}</span>
                            )}
                          </div>
                        </div>
                        <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0 ml-2" />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Job Matching Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="h-5 w-5" />
                AI 求人マッチング
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!matchResult && !matching && (
                <div className="text-center py-6">
                  <Briefcase className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground mb-4">
                    候補者の転職理由・希望条件・面談データをもとに、
                    <br className="hidden sm:block" />
                    最適な求人をAIが多角的に分析・推薦します
                  </p>
                  <Button onClick={handleJobMatch} disabled={matching}>
                    <Sparkles className="h-4 w-4 mr-2" />
                    AIマッチング分析を実行
                  </Button>
                </div>
              )}

              {matching && (
                <div className="flex flex-col items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
                  <p className="text-sm font-medium">分析中...</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    ADKエージェントが候補者データと求人情報を照合しています（10-30秒程度）
                  </p>
                </div>
              )}

              {matchError && (
                <div className="text-center py-6">
                  <p className="text-sm text-destructive mb-4">{matchError}</p>
                  <Button variant="outline" onClick={handleJobMatch}>
                    再試行
                  </Button>
                </div>
              )}

              {matchResult && (
                <div className="space-y-4">
                  {/* Analysis Summary */}
                  {matchResult.analysis_text && (
                    <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
                      <h4 className="text-sm font-semibold mb-2">分析サマリー</h4>
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">
                        {matchResult.analysis_text}
                      </p>
                    </div>
                  )}

                  {/* Data sources & module version */}
                  {(matchResult.data_sources_used?.length > 0 || matchResult.jd_module_version) && (
                    <div className="flex flex-wrap gap-1.5">
                      {matchResult.jd_module_version && (
                        <Badge variant="outline" className="text-xs">
                          JDモジュール: {matchResult.jd_module_version === "old" ? "JOB (旧)" : "JobDescription (新)"}
                        </Badge>
                      )}
                      {matchResult.data_sources_used?.map((src) => (
                        <Badge key={src} variant="secondary" className="text-xs">
                          {src === "zoho_jd" ? "Zoho求人票" : src === "semantic" ? "セマンティック" : src === "gmail" ? "Gmail" : src === "slack" ? "Slack" : src}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Top matches */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold">
                        推薦求人 ({matchResult.total_found}件)
                      </h4>
                      <Button variant="ghost" size="sm" onClick={handleJobMatch} disabled={matching}>
                        <Sparkles className="h-3 w-3 mr-1" />
                        再分析
                      </Button>
                    </div>
                    {matchResult.recommended_jobs.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4 text-center">
                        条件に合う求人が見つかりませんでした
                      </p>
                    ) : (
                      matchResult.recommended_jobs.map((job, index) => (
                        <JobMatchCard
                          key={`${job.company_name}-${job.job_name}-${index}`}
                          job={job}
                          rank={index + 1}
                        />
                      ))
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ---- Sub-components ----

function RenderValue({ value, fieldKey }: { value: unknown; fieldKey: string }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-muted-foreground">-</span>;
  }
  // Special handling for channel
  if (fieldKey === "field14") {
    return <span>{getChannelLabel(String(value))}</span>;
  }
  // Special handling for status
  if (fieldKey === "customer_status") {
    return <Badge variant={getStatusVariant(String(value))}>{getStatusLabel(String(value))}</Badge>;
  }
  if (typeof value === "object" && !Array.isArray(value)) {
    const obj = value as Record<string, unknown>;
    return <span>{obj.name ? String(obj.name) : JSON.stringify(value)}</span>;
  }
  return <span className="break-words">{String(value)}</span>;
}

function RenderStructuredValue({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-muted-foreground">-</span>;
  }
  if (Array.isArray(value)) {
    return (
      <div className="flex flex-wrap gap-1">
        {value.map((v, i) => (
          <Badge key={i} variant="secondary" className="text-xs max-w-full">
            <span className="break-words whitespace-normal leading-tight">{String(v)}</span>
          </Badge>
        ))}
      </div>
    );
  }
  return <span className="break-words whitespace-normal leading-relaxed">{String(value)}</span>;
}

function JobMatchCard({ job, rank }: { job: JobMatch; rank: number }) {
  const scoreColor =
    job.match_score >= 0.7
      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
      : job.match_score >= 0.5
        ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
        : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200";

  const sourceLabel: Record<string, string> = {
    zoho_jd: "Zoho求人票",
    semantic: "セマンティック",
    gmail: "Gmail",
    slack: "Slack",
  };

  return (
    <div className="border rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0">
          <span className="text-lg font-bold text-muted-foreground shrink-0">#{rank}</span>
          <div className="min-w-0">
            <h5 className="font-semibold truncate">{job.company_name}</h5>
            {job.job_name && job.job_name !== job.company_name && (
              <p className="text-xs text-muted-foreground truncate">{job.job_name}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {job.hiring_appetite && (
            <Badge variant={job.hiring_appetite === "緊急" ? "destructive" : "outline"} className="text-xs">
              {job.hiring_appetite}
            </Badge>
          )}
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${scoreColor}`}>
            {(job.match_score * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Recommendation Reason */}
      {job.recommendation_reason && (
        <p className="text-sm text-muted-foreground leading-relaxed">
          {job.recommendation_reason}
        </p>
      )}

      {/* Metadata */}
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        {job.salary_range && (
          <div className="flex items-center gap-1">
            <Wallet className="h-3 w-3" />
            <span>{job.salary_range}</span>
          </div>
        )}
        {job.location && (
          <div className="flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            <span>{job.location}</span>
          </div>
        )}
        {job.position && (
          <div className="flex items-center gap-1">
            <Briefcase className="h-3 w-3" />
            <span>{job.position}</span>
          </div>
        )}
        {job.remote && (
          <Badge variant="outline" className="text-xs">リモート: {job.remote}</Badge>
        )}
        {job.source && (
          <Badge variant="secondary" className="text-xs">{sourceLabel[job.source] || job.source}</Badge>
        )}
      </div>

      {/* Appeal Points */}
      {job.appeal_points.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {job.appeal_points.map((point, i) => (
            <Badge key={i} variant="secondary" className="text-xs max-w-full">
              <span className="break-words whitespace-normal leading-tight">{point}</span>
            </Badge>
          ))}
        </div>
      )}

      {/* Concerns */}
      {job.concerns.length > 0 && (
        <div className="space-y-1">
          {job.concerns.map((concern, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
              <span className="break-words">{concern}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
