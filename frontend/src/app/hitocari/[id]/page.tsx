"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { CandidateSearchDialog } from "@/components/candidate-search-dialog";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Loader2,
  Eye,
  ArrowLeft,
  ExternalLink,
  Sparkles,
  UserCheck,
  AlertCircle,
  Search,
  Mail,
  Calendar,
} from "lucide-react";
import { 
  apiClient, 
  Meeting, 
  StructuredData, 
  ZohoCandidate,
  extractNamesFromTitle,
  createCandidateSearchVariations 
} from "@/lib/api";
import { formatDistanceToNow, parseISO } from "date-fns";
import { ja } from "date-fns/locale";
import toast from "react-hot-toast";
import { SidebarTrigger } from "@/components/ui/sidebar";

// UI表示順と日本語ラベルの定義
const uiSections = [
  { title: '転職活動状況', items: [
    { key: 'transfer_activity_status', label: '転職活動状況' },
    { key: 'agent_count', label: '何名のエージェントと話したか' },
    { key: 'current_agents', label: 'すでに利用しているエージェントの社名' },
    { key: 'introduced_jobs', label: '他社エージェントに紹介された求人' },
    { key: 'job_appeal_points', label: '紹介求人の魅力点' },
    { key: 'job_concerns', label: '紹介求人の懸念点' },
    { key: 'companies_in_selection', label: 'すでに選考中の企業名/フェーズ' },
    { key: 'other_offer_salary', label: '他社オファー年収見込み' },
    { key: 'other_company_intention', label: '他社意向度及び見込み' },
    { key: 'transfer_reasons', label: '転職検討理由（複数選択可）' },
    { key: 'transfer_trigger', label: '転職検討理由 / きっかけ' },
    { key: 'desired_timing', label: '転職希望の時期' },
    { key: 'timing_details', label: '転職希望時期の詳細' },
    { key: 'current_job_status', label: '現職状況' },
    { key: 'transfer_status_memo', label: 'フリーメモ（転職状況）' },
  ]},
  { title: '転職軸（最重要）', items: [
    { key: 'transfer_axis_primary', label: '転職軸（最重要）' },
    { key: 'transfer_priorities', label: '転職軸（オープン）' },
  ]},
  { title: 'ヒアリング（現職）', items: [
    { key: 'career_history', label: '職歴' },
    { key: 'experience_industry', label: '経験業界' },
    { key: 'experience_field_hr', label: '経験領域（人材）' },
    { key: 'current_duties', label: '現職での担当業務' },
    { key: 'company_good_points', label: '現職企業の良いところ' },
    { key: 'company_bad_points', label: '現職企業の悪いところ' },
    { key: 'enjoyed_work', label: 'これまでの仕事で楽しかったこと/好きだったこと' },
    { key: 'difficult_work', label: 'これまでの仕事で辛かったこと/嫌だったこと' },
  ]},
  { title: '転職軸（業界・職種）', items: [
    { key: 'desired_industry', label: '希望業界' },
    { key: 'industry_reason', label: '業界希望理由' },
    { key: 'desired_position', label: '希望職種' },
    { key: 'ca_ra_focus', label: 'CA起点/RA起点' },
    { key: 'customer_acquisition', label: '集客方法/比率' },
    { key: 'new_existing_ratio', label: '新規/既存の比率' },
    { key: 'position_industry_reason', label: '職種・業界希望理由' },
  ]},
  { title: '転職軸（給与）', items: [
    { key: 'current_salary', label: '現年収（数字のみ）' },
    { key: 'salary_breakdown', label: '現年収内訳' },
    { key: 'desired_first_year_salary', label: '初年度希望年収（数字）' },
    { key: 'base_incentive_ratio', label: '基本給・インセンティブ比率' },
    { key: 'max_future_salary', label: '将来的な年収の最大値' },
    { key: 'salary_memo', label: 'フリーメモ（給与）' },
  ]},
  { title: '転職軸（リモート・時間）', items: [
    { key: 'remote_time_memo', label: 'フリーメモ（リモート・時間）' },
  ]},
  { title: '転職軸（会社カルチャー・規模）', items: [
    { key: 'business_vision', label: '事業構想' },
    { key: 'desired_employee_count', label: '希望従業員数' },
    { key: 'culture_scale_memo', label: 'フリーメモ（会社カルチャー・規模）' },
  ]},
  { title: '転職軸（将来的なキャリアパス）', items: [
    { key: 'career_vision', label: 'キャリアビジョン' },
  ]},
];

interface CandidateMatchSuggestion {
  candidate: ZohoCandidate;
  confidence: number;
  matchedNames: string[];
}

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const meetingId = params.id as string;

  // States
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [structuredData, setStructuredData] = useState<StructuredData | null>(null);
  const [candidateSuggestions, setCandidateSuggestions] = useState<CandidateMatchSuggestion[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<ZohoCandidate | null>(null);
  const [processing, setProcessing] = useState(false);
  const [extractOnlyProcessing, setExtractOnlyProcessing] = useState(false);
  const [zohoSyncProcessing, setZohoSyncProcessing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingStructured, setLoadingStructured] = useState(false);
  const [showCandidateSearch, setShowCandidateSearch] = useState(false);
  const [isEditingTranscript, setIsEditingTranscript] = useState(false);
  const [transcriptSaving, setTranscriptSaving] = useState(false);
  const [draftTranscript, setDraftTranscript] = useState("");
  const [transcriptProvider, setTranscriptProvider] = useState("");

  // Load meeting data on mount
  useEffect(() => {
    if (meetingId) {
      loadMeetingDetail();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingId]);

  const loadMeetingDetail = async () => {
    try {
      setLoading(true);
      const fullMeeting = await apiClient.getMeeting(meetingId);
      setSelectedMeeting(fullMeeting);
      setStructuredData(null);
      setCandidateSuggestions([]);
      setSelectedCandidate(null);
      setDraftTranscript(fullMeeting.text_content || "");
      const provider =
        (fullMeeting as any)?.metadata?.transcript_provider ||
        (fullMeeting as any)?.metadata?.transcriptProvider ||
        "";
      setTranscriptProvider(provider);

      setLoadingStructured(true);
      const data = await apiClient.getStructuredData(fullMeeting.id);
      if (data && data.data && Object.keys(data.data).length > 0) {
        setStructuredData(data);
        // 既存の構造化データがある場合、対応する候補者を自動選択
        if (data.zoho_candidate) {
          const existingCandidate: ZohoCandidate = {
            record_id: data.zoho_candidate.record_id || '',
            candidate_id: data.zoho_candidate.candidate_id || '',
            candidate_name: data.zoho_candidate.candidate_name || '',
            candidate_email: data.zoho_candidate.candidate_email || '',
          };
          setSelectedCandidate(existingCandidate);
        }
      } else {
        await generateCandidateSuggestions(fullMeeting);
      }
    } catch (error) {
      console.error('Failed to load meeting detail:', error);
      toast.error('議事録の詳細を取得できませんでした');
      router.push('/hitocari');
    } finally {
      setLoading(false);
      setLoadingStructured(false);
    }
  };

  const generateCandidateSuggestions = async (meeting: Meeting) => {
    if (!meeting.title) return;

    try {
      const extractedNames = extractNamesFromTitle(meeting.title);
      if (extractedNames.length === 0) return;

      const searchVariations = createCandidateSearchVariations(extractedNames);
      const suggestions: CandidateMatchSuggestion[] = [];

      const isZohoLikeError = (e: unknown): e is { status?: number; message?: string } =>
        typeof e === 'object' && e !== null && ('status' in e || 'message' in e);

      for (const nameVariation of searchVariations.slice(0, 3)) {
        try {
          const results = await apiClient.searchZohoCandidates(nameVariation, 5);
          
          results.items.forEach(candidate => {
            const confidence = calculateNameSimilarity(extractedNames, candidate.candidate_name);
            if (confidence > 0.3) {
              const existingSuggestion = suggestions.find(s => s.candidate.record_id === candidate.record_id);
              if (!existingSuggestion) {
                suggestions.push({
                  candidate,
                  confidence,
                  matchedNames: extractedNames,
                });
              }
            }
          });
        } catch (error: unknown) {
          if (isZohoLikeError(error) && (error.status === 500 || error.status === 502 || error.message?.includes('Zoho'))) {
            console.warn(`Zoho search unavailable for "${nameVariation}":`, error.message || error);
            if (searchVariations.indexOf(nameVariation) === 0) {
              toast.error('Zoho CRM連携が一時的に利用できません。手動で候補者を選択してください。', {
                duration: 6000,
              });
            }
          } else {
            console.warn(`Search failed for name variation: ${nameVariation}`, error);
          }
        }
      }

      suggestions.sort((a, b) => b.confidence - a.confidence);
      setCandidateSuggestions(suggestions.slice(0, 5));
    } catch (error) {
      console.error('Failed to generate candidate suggestions:', error);
    }
  };

  const calculateNameSimilarity = (extractedNames: string[], candidateName: string): number => {
    if (!candidateName) return 0;

    let maxSimilarity = 0;
    const candidateNormalized = candidateName.toLowerCase().replace(/\s+/g, '');

    for (const extracted of extractedNames) {
      const extractedNormalized = extracted.toLowerCase().replace(/\s+/g, '');
      
      if (extractedNormalized === candidateNormalized) {
        return 1.0;
      }

      if (candidateNormalized.includes(extractedNormalized) || extractedNormalized.includes(candidateNormalized)) {
        maxSimilarity = Math.max(maxSimilarity, 0.8);
      }

      const commonChars = extractedNormalized.split('').filter(char => candidateNormalized.includes(char)).length;
      const overlapRatio = commonChars / Math.max(extractedNormalized.length, candidateNormalized.length);
      maxSimilarity = Math.max(maxSimilarity, overlapRatio * 0.6);
    }

    return maxSimilarity;
  };

  const handleProcessStructured = async () => {
    if (!selectedMeeting || !selectedCandidate) return;

    try {
      setProcessing(true);
      const result = await apiClient.processStructuredData(selectedMeeting.id, {
        zoho_candidate_id: selectedCandidate.candidate_id,
        zoho_record_id: selectedCandidate.record_id,
        zoho_candidate_name: selectedCandidate.candidate_name,
        zoho_candidate_email: selectedCandidate.candidate_email,
      });

      setStructuredData(result);
      setCandidateSuggestions([]);
      
      toast.success('構造化処理が完了しました');
    } catch (error) {
      console.error('Failed to process structured data:', error);
      toast.error('構造化処理に失敗しました');
    } finally {
      setProcessing(false);
    }
  };

  const handleSaveTranscript = async () => {
    if (!selectedMeeting) return;
    try {
      setTranscriptSaving(true);
      const updated = await apiClient.updateTranscript(selectedMeeting.id, {
        text_content: draftTranscript.trim(),
        transcript_provider: transcriptProvider || undefined,
        delete_structured: true,
      });
      setSelectedMeeting(updated);
      setStructuredData(null); // 旧構造化結果をクリア
      toast.success("議事録を更新しました。再度「再実行」で構造化してください。");
      setIsEditingTranscript(false);
    } catch (error) {
      console.error("Failed to update transcript:", error);
      toast.error("議事録の保存に失敗しました");
    } finally {
      setTranscriptSaving(false);
    }
  };

  const handleExtractOnlyStructured = async () => {
    if (!selectedMeeting) return;

    try {
      setExtractOnlyProcessing(true);
      const result = await apiClient.extractStructuredDataOnly(selectedMeeting.id, {});

      // Convert StructuredDataOnly to StructuredData format
      const convertedResult: StructuredData = {
        meeting_id: result.meeting_id,
        data: result.data,
        custom_schema_id: result.custom_schema_id,
        schema_version: result.schema_version,
        zoho_candidate: undefined // Zoho候補者情報はなし
      };

      setStructuredData(convertedResult);
      setCandidateSuggestions([]);
      
      toast.success('構造化出力が完了しました（Zoho同期なし）');
    } catch (error) {
      console.error('Failed to extract structured data only:', error);
      toast.error('構造化出力に失敗しました');
    } finally {
      setExtractOnlyProcessing(false);
    }
  };

  const handleSyncToZoho = async () => {
    if (!selectedMeeting || !selectedCandidate || !structuredData) return;

    try {
      setZohoSyncProcessing(true);
      const result = await apiClient.syncStructuredDataToZoho(selectedMeeting.id, {
        zoho_candidate_id: selectedCandidate.candidate_id,
        zoho_record_id: selectedCandidate.record_id,
        zoho_candidate_name: selectedCandidate.candidate_name,
        zoho_candidate_email: selectedCandidate.candidate_email,
      });

      // Update structured data with Zoho candidate info
      setStructuredData(prev => prev ? {
        ...prev,
        zoho_candidate: result.zoho_candidate
      } : prev);

      if (result.zoho_sync_result.status === 'success') {
        const updatedCount = result.zoho_sync_result.updated_fields_count || 0;
        const syncedCount = result.synced_data_fields?.length || 0;
        toast.success(`Zoho同期が完了しました（送信: ${syncedCount}フィールド、更新: ${updatedCount}フィールド）`, {
          duration: 5000
        });
      } else {
        toast.error(`Zoho同期に失敗しました: ${result.zoho_sync_result.message}`, {
          duration: 8000
        });
      }
    } catch (error) {
      console.error('Failed to sync to Zoho:', error);
      toast.error('Zoho同期に失敗しました');
    } finally {
      setZohoSyncProcessing(false);
    }
  };

  const formatDateTime = (dateString: string) => {
    try {
      const date = parseISO(dateString);
      return formatDistanceToNow(date, { addSuffix: true, locale: ja });
    } catch {
      return dateString;
    }
  };

  const renderStructuredValue = (value: unknown) => {
    if (value === null || value === undefined || value === '') {
      return <span className="text-muted-foreground">-</span>;
    }
    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-muted-foreground">-</span>;
      return (
        <div className="flex flex-wrap gap-1">
          {value.map((v, i) => {
            const stringValue = String(v);
            return (
              <Badge key={i} variant="secondary" className="text-xs max-w-full">
                <span className="break-words whitespace-normal leading-tight">
                  {stringValue}
                </span>
              </Badge>
            );
          })}
        </div>
      );
    }
    return <span className="break-words whitespace-normal leading-relaxed">{String(value)}</span>;
  };

  if (loading) {
    return (
      <div className="w-full px-6 py-6">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">議事録を読み込み中...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!selectedMeeting) {
    return (
      <div className="w-full px-6 py-6">
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">議事録が見つかりませんでした</p>
          <Link href="/hitocari">
            <Button>議事録一覧に戻る</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="w-full px-6 py-6">
        <div className="space-y-6">
          {/* Header with Back Button */}
          <div className="flex items-center space-x-4 min-w-0">
            <div className="flex items-center space-x-2">
              <SidebarTrigger className="md:hidden" />
              <Link href="/hitocari">
                <Button variant="ghost" size="sm" className="shrink-0">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  議事録一覧に戻る
                </Button>
              </Link>
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl font-bold truncate">{selectedMeeting.title || '(無題)'}</h1>
              <p className="text-muted-foreground truncate">議事録の詳細情報と構造化処理</p>
            </div>
          </div>

          {/* Meeting Header Info */}
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Badge variant={structuredData ? "default" : "secondary"}>
                      {structuredData ? "構造化済み" : "未処理"}
                    </Badge>
                    {selectedMeeting.document_url && (
                      <Button asChild variant="outline" size="sm">
                        <a href={selectedMeeting.document_url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-4 w-4 mr-2" />
                          ドキュメント
                        </a>
                      </Button>
                    )}
                  </div>
                  
                  <div className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
                    <div className="flex items-center space-x-1 min-w-0">
                      <Mail className="h-4 w-4 shrink-0" />
                      <span className="truncate">{selectedMeeting.organizer_email}</span>
                    </div>
                    {selectedMeeting.meeting_datetime && (
                      <div className="flex items-center space-x-1 shrink-0">
                        <Calendar className="h-4 w-4" />
                        <span>{formatDateTime(selectedMeeting.meeting_datetime)}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardHeader>
            
            {selectedMeeting.invited_emails.length > 0 && (
              <CardContent className="pt-0">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">参加者 ({selectedMeeting.invited_emails.length}名)</Label>
                  <div className="flex flex-wrap gap-2">
                    {selectedMeeting.invited_emails.map((email, index) => (
                      <Badge key={index} variant="outline" className="max-w-xs">
                        <span className="truncate">{email}</span>
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Content Area */}
          <div className="grid gap-6 xl:grid-cols-2">
            {/* Processing Section */}
            <div className="space-y-6 min-w-0">
              {loadingStructured ? (
                <Card>
                  <CardContent className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
                      <p className="text-muted-foreground">構造化データを確認中...</p>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <>
                  {structuredData && structuredData.data && Object.keys(structuredData.data).length > 0 && (
                    <StructuredDataCard data={structuredData} />
                  )}
                  <CandidateSelectionCard />
                </>
              )}
            </div>

            {/* Preview Section */}
            <div className="space-y-6 min-w-0">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0">
                  <div className="flex items-center space-x-2">
                    <Eye className="h-5 w-5" />
                    <CardTitle className="text-base sm:text-lg">議事録プレビュー</CardTitle>
                  </div>
                  <div className="flex gap-2">
                    {structuredData === null && (
                      <Badge variant="secondary" className="hidden sm:inline-flex">テキスト更新済み</Badge>
                    )}
                    {isEditingTranscript ? (
                      <>
                        <Button
                          size="sm"
                          onClick={handleSaveTranscript}
                          disabled={transcriptSaving}
                        >
                          {transcriptSaving ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              保存中...
                            </>
                          ) : (
                            "保存して閉じる"
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setIsEditingTranscript(false);
                            setDraftTranscript(selectedMeeting.text_content || "");
                          }}
                          disabled={transcriptSaving}
                        >
                          キャンセル
                        </Button>
                      </>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => setIsEditingTranscript(true)}>
                        編集
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {isEditingTranscript ? (
                    <>
                      <div className="space-y-2">
                        <Label className="text-sm">文字起こしテキスト</Label>
                        <Textarea
                          value={draftTranscript}
                          onChange={(e) => setDraftTranscript(e.target.value)}
                          className="min-h-[260px]"
                          placeholder="ここに議事録テキストを貼り付けてください"
                        />
                        <div className="text-xs text-muted-foreground text-right">
                          {draftTranscript.length.toLocaleString()} 文字
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label className="text-sm">文字起こし提供元（任意）</Label>
                        <Input
                          value={transcriptProvider}
                          onChange={(e) => setTranscriptProvider(e.target.value)}
                          placeholder="例: Notta, Google Meet, 文字起こしメモなど"
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        保存するとSupabase上の議事録本文が上書きされ、既存の構造化結果はクリアされます。左の「再実行」で最新本文を基に構造化してください。
                      </p>
                    </>
                  ) : (
                    <ScrollArea className="h-96 w-full rounded-md border p-4">
                      <pre className="whitespace-pre-wrap text-sm break-words overflow-hidden">
                        {selectedMeeting.text_content || "まだ本文がありません。編集を押して貼り付けてください。"}
                      </pre>
                    </ScrollArea>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>

      {/* Candidate Search Dialog */}
      <CandidateSearchDialog
        open={showCandidateSearch}
        onOpenChange={setShowCandidateSearch}
        onCandidateSelect={setSelectedCandidate}
        selectedCandidate={selectedCandidate}
      />
    </>
  );

  function StructuredDataCard({ data }: { data: StructuredData }) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1.5">
              <CardTitle className="flex items-center space-x-2">
                <Sparkles className="h-5 w-5 text-green-600" />
                <span>構造化出力</span>
              </CardTitle>
              <CardDescription>
                AI による議事録の構造化データ抽出結果
              </CardDescription>
            </div>
            <div className="flex gap-2">
              {/* 手動Zoho同期ボタン（常に表示） */}
              <Button 
                onClick={handleSyncToZoho}
                disabled={!selectedCandidate || zohoSyncProcessing}
                variant={data.zoho_candidate ? "outline" : "default"}
                size="sm"
                className="shrink-0"
              >
                {zohoSyncProcessing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    同期中...
                  </>
                ) : selectedCandidate ? (
                  <>
                    <UserCheck className="h-4 w-4 mr-2" />
                    {data.zoho_candidate ? 'Zoho再同期' : 'Zoho同期'}
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4 mr-2" />
                    候補者を選択
                  </>
                )}
              </Button>
              
              {/* 既存の再実行ボタン */}
              <Button 
                onClick={handleProcessStructured}
                disabled={!selectedCandidate || processing}
                variant="outline"
                size="sm"
                className="shrink-0"
              >
                {processing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    処理中...
                  </>
                ) : selectedCandidate ? (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    再実行
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4 mr-2" />
                    候補者を選択
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 sm:space-y-6 p-4 sm:p-6">
          {/* Zoho候補者情報セクション */}
          {data.zoho_candidate && (
            <div className="space-y-3">
              <h4 className="text-sm sm:text-base font-semibold text-foreground">Zoho CRM 候補者情報</h4>
              <div className="grid grid-cols-1 border border-border rounded-lg overflow-hidden">
                {[
                  { key: 'candidate_name', label: '候補者名' },
                  { key: 'candidate_id', label: '候補者ID' },
                  { key: 'record_id', label: 'レコードID' },
                  { key: 'candidate_email', label: 'メールアドレス' },
                ].map((field, index) => (
                  <div key={field.key} className={`flex flex-col sm:grid sm:grid-cols-[140px_1fr] lg:grid-cols-[180px_1fr] ${index > 0 ? 'border-t border-border' : ''}`}>
                    <div className="bg-muted/30 px-3 py-2 text-xs sm:text-sm font-medium text-muted-foreground sm:border-r border-border">
                      {field.label}
                    </div>
                    <div className="px-3 py-2 text-xs sm:text-sm border-t sm:border-t-0 border-border sm:border-0 min-w-0">
                      <div className="break-words overflow-wrap-anywhere">
                        {renderStructuredValue(data.zoho_candidate?.[field.key as keyof typeof data.zoho_candidate])}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* 構造化データセクション */}
          <div className="space-y-4">
            {uiSections.map((section) => {
              const sectionHasData = section.items.some(item => data.data[item.key]);
              if (!sectionHasData) return null;

              return (
                <div key={section.title} className="space-y-3">
                  <h4 className="text-sm sm:text-base font-semibold text-foreground">{section.title}</h4>
                  <div className="grid grid-cols-1 border border-border rounded-lg overflow-hidden">
                    {section.items.map((item, index) => {
                      const value = data.data[item.key];
                      if (value === null || value === undefined || value === '') return null;
                      
                      return (
                        <div key={item.key} className={`flex flex-col sm:grid sm:grid-cols-[140px_1fr] lg:grid-cols-[180px_1fr] ${index > 0 ? 'border-t border-border' : ''}`}>
                          <div className="bg-muted/30 px-3 py-2 text-xs sm:text-sm font-medium text-muted-foreground sm:border-r border-border">
                            {item.label}
                          </div>
                          <div className="px-3 py-2 text-xs sm:text-sm border-t sm:border-t-0 border-border sm:border-0 min-w-0">
                            <div className="break-words overflow-wrap-anywhere">
                              {renderStructuredValue(value)}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    );
  }

  function CandidateSelectionCard() {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <UserCheck className="h-5 w-5" />
            <span>求職者の選択</span>
          </CardTitle>
          <CardDescription>
            {structuredData && structuredData.data && Object.keys(structuredData.data).length > 0 
              ? "構造化処理を再実行するために、対応する求職者を選択してください"
              : "構造化処理を行う前に、対応する求職者を選択してください"
            }
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Candidate Suggestions */}
          {candidateSuggestions.length > 0 && (
            <div className="space-y-3">
              <Label className="text-sm font-medium">会議名から推測された候補者</Label>
              <div className="space-y-2">
                {candidateSuggestions.map((suggestion) => (
                  <Card 
                    key={suggestion.candidate.record_id}
                    className={`cursor-pointer transition-all ${
                      selectedCandidate?.record_id === suggestion.candidate.record_id 
                        ? 'ring-2 ring-primary bg-primary/5' 
                        : 'hover:bg-muted/50'
                    }`}
                    onClick={() => setSelectedCandidate(suggestion.candidate)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="font-medium truncate">{suggestion.candidate.candidate_name}</div>
                          <div className="text-sm text-muted-foreground truncate">
                            ID: {suggestion.candidate.candidate_id}
                          </div>
                        </div>
                        <Badge variant={suggestion.confidence > 0.7 ? "default" : "secondary"} className="shrink-0">
                          {Math.round(suggestion.confidence * 100)}% 一致
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Manual Search */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">手動で候補者を検索</Label>
            <Button 
              variant="outline" 
              onClick={() => setShowCandidateSearch(true)}
              className="w-full"
            >
              <Search className="h-4 w-4 mr-2" />
              Zoho CRM で候補者を検索
            </Button>
            {selectedCandidate && !candidateSuggestions.some(s => s.candidate.record_id === selectedCandidate.record_id) && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="text-xs sm:text-sm font-medium text-green-800 truncate">
                  手動選択: {selectedCandidate.candidate_name}
                </div>
                <div className="text-xs text-green-700 mt-1 truncate">
                  ID: {selectedCandidate.candidate_id}
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <Separator />
          <div className="space-y-3">
            {/* 構造化出力専用ボタン */}
            <Button 
              onClick={handleExtractOnlyStructured}
              disabled={extractOnlyProcessing}
              variant="secondary"
              className="w-full h-12 sm:h-10 text-sm sm:text-base"
            >
              {extractOnlyProcessing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  構造化出力中...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  構造化出力のみ実行（Zoho同期なし）
                </>
              )}
            </Button>
            
            {/* 既存の構造化処理ボタン */}
            <Button 
              onClick={handleProcessStructured}
              disabled={!selectedCandidate || processing}
              className="w-full h-12 sm:h-10 text-sm sm:text-base"
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  構造化処理中...
                </>
              ) : selectedCandidate ? (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  {selectedCandidate.candidate_name} で構造化処理を{structuredData && structuredData.data && Object.keys(structuredData.data).length > 0 ? '再実行' : '実行'}
                </>
              ) : (
                <>
                  <AlertCircle className="h-4 w-4 mr-2" />
                  候補者を選択してください
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }
}
