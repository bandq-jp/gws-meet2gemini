"use client";

import { useState, useEffect, useMemo } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { CandidateSearchDialog } from "@/components/candidate-search-dialog";
import { Separator } from "@/components/ui/separator";
import {
  Download,
  Search,
  Filter,
  RefreshCw,
  FileText,
  Clock,
  User,
  Mail,
  Calendar,
  ExternalLink,
  Sparkles,
  UserCheck,
  AlertCircle,
  Loader2,
  Eye,
  Settings,
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

interface CandidateMatchSuggestion {
  candidate: ZohoCandidate;
  confidence: number;
  matchedNames: string[];
}

export default function HitocariPage() {
  const { isLoaded, userId } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAllAccounts, setShowAllAccounts] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [structuredData, setStructuredData] = useState<StructuredData | null>(null);
  const [candidateSuggestions, setCandidateSuggestions] = useState<CandidateMatchSuggestion[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<ZohoCandidate | null>(null);
  const [processing, setProcessing] = useState(false);
  const [loadingStructured, setLoadingStructured] = useState(false);
  const [showCandidateSearch, setShowCandidateSearch] = useState(false);

  const userEmail = user?.emailAddresses[0]?.emailAddress;

  // Define loadMeetings function before it's used in useEffect
  const loadMeetings = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getMeetings();
      setMeetings(data);
    } catch (error) {
      console.error('Failed to load meetings:', error);
      toast.error(`議事録の読み込みに失敗しました: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Filter meetings based on search and account filter - Move useMemo before early returns
  const filteredMeetings = useMemo(() => {
    let filtered = meetings;

    // Filter by user account if not showing all accounts
    if (!showAllAccounts && userEmail) {
      filtered = filtered.filter(meeting => meeting.organizer_email === userEmail);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(meeting =>
        meeting.title?.toLowerCase().includes(query) ||
        meeting.organizer_email?.toLowerCase().includes(query) ||
        meeting.invited_emails?.some(email => email.toLowerCase().includes(query)) ||
        meeting.text_content?.toLowerCase().includes(query)
      );
    }

    return filtered.sort((a, b) => 
      new Date(b.meeting_datetime || b.created_at).getTime() - 
      new Date(a.meeting_datetime || a.created_at).getTime()
    );
  }, [meetings, searchQuery, showAllAccounts, userEmail]);

  // Separate structured and unstructured meetings
  const { structuredMeetings, unstructuredMeetings } = useMemo(() => {
    const structured: Meeting[] = [];
    const unstructured: Meeting[] = [];

    // This is a simple implementation - in a real app, you'd track which meetings have structured data
    filteredMeetings.forEach(meeting => {
      // For now, assume meeting has structured data if it has certain metadata
      if (meeting.metadata && Object.keys(meeting.metadata).length > 0) {
        structured.push(meeting);
      } else {
        unstructured.push(meeting);
      }
    });

    return { structuredMeetings: structured, unstructuredMeetings: unstructured };
  }, [filteredMeetings]);

  // Auth protection
  useEffect(() => {
    if (isLoaded && !userId) {
      router.push('/sign-in');
      return;
    }

    if (isLoaded && user && userId) {
      const userEmail = user.emailAddresses[0]?.emailAddress;
      if (userEmail && !userEmail.endsWith('@bandq.jp')) {
        router.push('/unauthorized');
        return;
      }
    }
  }, [isLoaded, userId, user, router]);

  // Load meetings on component mount - Move this before conditional returns
  useEffect(() => {
    loadMeetings();
  }, []);

  // Show loading state while auth is loading
  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">読み込み中...</p>
        </div>
      </div>
    );
  }

  // If not authenticated, don't render anything (redirect will happen)
  if (!userId) {
    return null;
  }

  const handleCollectMeetings = async () => {
    try {
      setCollecting(true);
      const accounts = showAllAccounts ? undefined : (userEmail ? [userEmail] : undefined);
      const result = await apiClient.collectMeetings(accounts, false, false);
      
      // Refresh meetings after collection
      await loadMeetings();
      
      toast.success(`${result.stored}件の議事録を取得しました`);
    } catch (error) {
      console.error('Failed to collect meetings:', error);
      toast.error(`議事録の取得に失敗しました: ${error.message}`);
    } finally {
      setCollecting(false);
    }
  };

  const handleMeetingSelect = async (meeting: Meeting) => {
    setSelectedMeeting(meeting);
    setStructuredData(null);
    setCandidateSuggestions([]);
    setSelectedCandidate(null);

    // Load structured data if exists
    try {
      setLoadingStructured(true);
      const data = await apiClient.getStructuredData(meeting.id);
      if (data && data.data && Object.keys(data.data).length > 0) {
        setStructuredData(data);
      } else {
        // Generate candidate suggestions for unstructured meetings
        await generateCandidateSuggestions(meeting);
      }
    } catch (error) {
      console.error('Failed to load structured data:', error);
      // Generate candidate suggestions even if structured data loading fails
      await generateCandidateSuggestions(meeting);
    } finally {
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

      // Search for candidates using name variations
      for (const nameVariation of searchVariations.slice(0, 3)) { // Limit searches
        try {
          const results = await apiClient.searchZohoCandidates(nameVariation, 5);
          
          results.items.forEach(candidate => {
            // Calculate confidence based on name similarity
            const confidence = calculateNameSimilarity(extractedNames, candidate.candidate_name);
            if (confidence > 0.3) { // Only include matches with reasonable confidence
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
        } catch (error) {
          console.warn(`Search failed for name variation: ${nameVariation}`, error);
        }
      }

      // Sort by confidence and limit results
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
      
      // Exact match
      if (extractedNormalized === candidateNormalized) {
        return 1.0;
      }

      // Contains match
      if (candidateNormalized.includes(extractedNormalized) || extractedNormalized.includes(candidateNormalized)) {
        maxSimilarity = Math.max(maxSimilarity, 0.8);
      }

      // Character overlap ratio
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
      
      // Refresh meetings to update structured status
      await loadMeetings();
    } catch (error) {
      console.error('Failed to process structured data:', error);
    } finally {
      setProcessing(false);
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

  const MeetingCard = ({ meeting, showActions = true }: { meeting: Meeting; showActions?: boolean }) => (
    <Card 
      className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
        selectedMeeting?.id === meeting.id ? 'ring-2 ring-primary' : ''
      }`}
      onClick={() => handleMeetingSelect(meeting)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-medium truncate">
              {meeting.title || '(無題)'}
            </CardTitle>
            <CardDescription className="flex items-center gap-2 mt-1">
              <User className="w-4 h-4" />
              {meeting.organizer_email}
              {meeting.meeting_datetime && (
                <>
                  <Clock className="w-4 h-4 ml-2" />
                  {formatDateTime(meeting.meeting_datetime)}
                </>
              )}
            </CardDescription>
          </div>
          <div className="flex flex-col items-end gap-1">
            <Badge variant={structuredData ? "default" : "secondary"}>
              {structuredData ? "構造化済み" : "未処理"}
            </Badge>
            {meeting.invited_emails.length > 0 && (
              <span className="text-xs text-muted-foreground">
                参加者 {meeting.invited_emails.length}名
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      
      {showActions && meeting.invited_emails.length > 0 && (
        <CardContent className="pt-0">
          <div className="flex flex-wrap gap-1">
            {meeting.invited_emails.slice(0, 3).map((email, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {email.split('@')[0]}
              </Badge>
            ))}
            {meeting.invited_emails.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{meeting.invited_emails.length - 3}
              </Badge>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );

  return (
    <AppShell activeTab="hitocari">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">ひとキャリ 議事録管理</h1>
            <p className="text-muted-foreground">
              Google Meet議事録の管理と構造化データ抽出
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              onClick={handleCollectMeetings}
              disabled={collecting}
              className="flex items-center gap-2"
            >
              {collecting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              {collecting ? "取得中..." : "Google Driveから取得"}
            </Button>
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={loadMeetings}
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              <Button variant="outline" size="icon" disabled>
                <Settings className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Panel - Meeting List */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    議事録一覧
                  </CardTitle>
                  <Badge variant="secondary">
                    {filteredMeetings.length}件
                  </Badge>
                </div>
                <CardDescription>
                  {showAllAccounts ? "全アカウント" : "自分のアカウント"}の議事録
                </CardDescription>
              </CardHeader>
              
              <CardContent className="space-y-4">
                {/* Search and Filter Controls */}
                <div className="space-y-3">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="議事録を検索..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="show-all"
                      checked={showAllAccounts}
                      onChange={(e) => setShowAllAccounts(e.target.checked)}
                      className="rounded"
                    />
                    <Label htmlFor="show-all" className="text-sm">
                      全ての議事録を表示
                    </Label>
                  </div>
                </div>

                <Separator />

                {/* Meeting List Tabs */}
                <Tabs defaultValue="all" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="all" className="text-xs">
                      全て ({filteredMeetings.length})
                    </TabsTrigger>
                    <TabsTrigger value="structured" className="text-xs">
                      構造化済み ({structuredMeetings.length})
                    </TabsTrigger>
                    <TabsTrigger value="unstructured" className="text-xs">
                      未処理 ({unstructuredMeetings.length})
                    </TabsTrigger>
                  </TabsList>
                  
                  <div className="mt-4 max-h-[600px] overflow-y-auto space-y-3">
                    <TabsContent value="all" className="space-y-3 mt-0">
                      {loading ? (
                        <div className="flex items-center justify-center py-8">
                          <Loader2 className="w-6 h-6 animate-spin" />
                          <span className="ml-2">読み込み中...</span>
                        </div>
                      ) : filteredMeetings.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                          <p>議事録が見つかりません</p>
                          <p className="text-sm">Google Driveから取得してください</p>
                        </div>
                      ) : (
                        filteredMeetings.map((meeting) => (
                          <MeetingCard key={meeting.id} meeting={meeting} />
                        ))
                      )}
                    </TabsContent>
                    
                    <TabsContent value="structured" className="space-y-3 mt-0">
                      {structuredMeetings.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-50" />
                          <p>構造化済み議事録がありません</p>
                        </div>
                      ) : (
                        structuredMeetings.map((meeting) => (
                          <MeetingCard key={meeting.id} meeting={meeting} />
                        ))
                      )}
                    </TabsContent>
                    
                    <TabsContent value="unstructured" className="space-y-3 mt-0">
                      {unstructuredMeetings.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          <UserCheck className="w-12 h-12 mx-auto mb-4 opacity-50" />
                          <p>未処理の議事録がありません</p>
                        </div>
                      ) : (
                        unstructuredMeetings.map((meeting) => (
                          <MeetingCard key={meeting.id} meeting={meeting} />
                        ))
                      )}
                    </TabsContent>
                  </div>
                </Tabs>
              </CardContent>
            </Card>
          </div>

          {/* Right Panel - Meeting Detail */}
          <div className="lg:col-span-2">
            {selectedMeeting ? (
              <div className="space-y-6">
                {/* Meeting Header */}
                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-xl mb-2">
                          {selectedMeeting.title || '(無題)'}
                        </CardTitle>
                        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            {selectedMeeting.meeting_datetime 
                              ? formatDateTime(selectedMeeting.meeting_datetime)
                              : '日時不明'
                            }
                          </div>
                          <div className="flex items-center gap-1">
                            <Mail className="w-4 h-4" />
                            {selectedMeeting.organizer_email}
                          </div>
                          {selectedMeeting.document_url && (
                            <Button asChild variant="outline" size="sm">
                              <a 
                                href={selectedMeeting.document_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="flex items-center gap-1"
                              >
                                <ExternalLink className="w-4 h-4" />
                                ドキュメント
                              </a>
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  
                  {selectedMeeting.invited_emails.length > 0 && (
                    <CardContent>
                      <Label className="text-sm font-medium">参加者</Label>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {selectedMeeting.invited_emails.map((email, index) => (
                          <Badge key={index} variant="outline">
                            {email}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  )}
                </Card>

                {/* Structured Data or Candidate Selection */}
                {loadingStructured ? (
                  <Card>
                    <CardContent className="flex items-center justify-center py-12">
                      <Loader2 className="w-6 h-6 animate-spin mr-2" />
                      構造化データを確認中...
                    </CardContent>
                  </Card>
                ) : structuredData && structuredData.data && Object.keys(structuredData.data).length > 0 ? (
                  /* Structured Data Display */
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-green-600" />
                        構造化出力
                      </CardTitle>
                      <CardDescription>
                        AI による議事録の構造化データ抽出結果
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {structuredData.zoho_candidate && (
                        <div className="mb-4 p-4 bg-muted rounded-lg">
                          <h4 className="font-medium mb-2">対応求職者</h4>
                          <div className="text-sm space-y-1">
                            <div><strong>名前:</strong> {structuredData.zoho_candidate.candidate_name}</div>
                            <div><strong>ID:</strong> {structuredData.zoho_candidate.candidate_id}</div>
                            {structuredData.zoho_candidate.candidate_email && (
                              <div><strong>メール:</strong> {structuredData.zoho_candidate.candidate_email}</div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      <div className="space-y-4">
                        {Object.entries(structuredData.data).map(([key, value]) => (
                          <div key={key} className="grid grid-cols-3 gap-4 py-2 border-b">
                            <div className="text-sm font-medium text-muted-foreground">
                              {key.replace(/_/g, ' ')}
                            </div>
                            <div className="col-span-2 text-sm">
                              {Array.isArray(value) ? value.join(', ') : String(value || '-')}
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  /* Candidate Selection for Unstructured Data */
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <UserCheck className="w-5 h-5" />
                        求職者の選択
                      </CardTitle>
                      <CardDescription>
                        構造化処理を行う前に、対応する求職者を選択してください
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Candidate Suggestions */}
                      {candidateSuggestions.length > 0 && (
                        <div>
                          <Label className="text-sm font-medium mb-3 block">
                            会議名から推測された候補者
                          </Label>
                          <div className="space-y-2">
                            {candidateSuggestions.map((suggestion) => (
                              <Card 
                                key={suggestion.candidate.record_id}
                                className={`cursor-pointer transition-colors ${
                                  selectedCandidate?.record_id === suggestion.candidate.record_id 
                                    ? 'ring-2 ring-primary bg-primary/5' 
                                    : 'hover:bg-muted/50'
                                }`}
                                onClick={() => setSelectedCandidate(suggestion.candidate)}
                              >
                                <CardContent className="p-3">
                                  <div className="flex items-center justify-between">
                                    <div>
                                      <div className="font-medium">
                                        {suggestion.candidate.candidate_name}
                                      </div>
                                      <div className="text-sm text-muted-foreground">
                                        ID: {suggestion.candidate.candidate_id}
                                      </div>
                                    </div>
                                    <div className="text-right">
                                      <Badge 
                                        variant={suggestion.confidence > 0.7 ? "default" : "secondary"}
                                      >
                                        {Math.round(suggestion.confidence * 100)}% 一致
                                      </Badge>
                                    </div>
                                  </div>
                                </CardContent>
                              </Card>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Manual Search */}
                      <div>
                        <Label className="text-sm font-medium mb-3 block">
                          手動で候補者を検索
                        </Label>
                        <Button 
                          variant="outline" 
                          onClick={() => setShowCandidateSearch(true)}
                          className="w-full"
                        >
                          <Search className="w-4 h-4 mr-2" />
                          Zoho CRM で候補者を検索
                        </Button>
                        {selectedCandidate && !candidateSuggestions.some(s => s.candidate.record_id === selectedCandidate.record_id) && (
                          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                            <div className="text-sm font-medium text-green-800">
                              手動選択: {selectedCandidate.candidate_name}
                            </div>
                            <div className="text-xs text-green-700 mt-1">
                              ID: {selectedCandidate.candidate_id}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Action Button */}
                      <div className="pt-4 border-t">
                        <Button 
                          onClick={handleProcessStructured}
                          disabled={!selectedCandidate || processing}
                          className="w-full"
                        >
                          {processing ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              構造化処理中...
                            </>
                          ) : selectedCandidate ? (
                            <>
                              <Sparkles className="w-4 h-4 mr-2" />
                              {selectedCandidate.candidate_name} で構造化処理を実行
                            </>
                          ) : (
                            <>
                              <AlertCircle className="w-4 h-4 mr-2" />
                              候補者を選択してください
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Meeting Content Preview */}
                {selectedMeeting.text_content && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Eye className="w-5 h-5" />
                        議事録プレビュー
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="bg-muted/30 rounded-lg p-4 max-h-80 overflow-y-auto">
                        <pre className="whitespace-pre-wrap text-sm text-foreground">
                          {selectedMeeting.text_content.substring(0, 1000)}
                          {selectedMeeting.text_content.length > 1000 && '...'}
                        </pre>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            ) : (
              /* No meeting selected */
              <Card className="h-96 flex items-center justify-center">
                <div className="text-center text-muted-foreground">
                  <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <h3 className="text-lg font-medium mb-2">議事録を選択</h3>
                  <p>左側から議事録を選択して詳細を表示します</p>
                </div>
              </Card>
            )}
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
    </AppShell>
  );
}