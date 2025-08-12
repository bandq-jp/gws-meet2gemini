"use client";

import { useState, useEffect, useMemo } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { ModernAppShell } from "@/components/modern-app-shell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { CandidateSearchDialog } from "@/components/candidate-search-dialog";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
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
  ArrowLeft,
  Users,
  Building,
  ChevronRight,
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

type ViewMode = 'list' | 'detail';

export default function EnhancedHitocariPage() {
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
  const [viewMode, setViewMode] = useState<ViewMode>('list');

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

  // Filter meetings based on search and account filter
  const filteredMeetings = useMemo(() => {
    let filtered = meetings;

    if (!showAllAccounts && userEmail) {
      filtered = filtered.filter(meeting => meeting.organizer_email === userEmail);
    }

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

    filteredMeetings.forEach(meeting => {
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

  // Load meetings on component mount
  useEffect(() => {
    loadMeetings();
  }, []);

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

  if (!userId) {
    return null;
  }

  const handleCollectMeetings = async () => {
    try {
      setCollecting(true);
      const accounts = showAllAccounts ? undefined : (userEmail ? [userEmail] : undefined);
      const result = await apiClient.collectMeetings(accounts, false, false);
      
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
    setViewMode('detail');

    try {
      setLoadingStructured(true);
      const data = await apiClient.getStructuredData(meeting.id);
      if (data && data.data && Object.keys(data.data).length > 0) {
        setStructuredData(data);
      } else {
        await generateCandidateSuggestions(meeting);
      }
    } catch (error) {
      console.error('Failed to load structured data:', error);
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
        } catch (error) {
          console.warn(`Search failed for name variation: ${nameVariation}`, error);
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
      
      await loadMeetings();
      toast.success('構造化処理が完了しました');
    } catch (error) {
      console.error('Failed to process structured data:', error);
      toast.error('構造化処理に失敗しました');
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

  const handleBackToList = () => {
    setViewMode('list');
    setSelectedMeeting(null);
    setStructuredData(null);
    setCandidateSuggestions([]);
    setSelectedCandidate(null);
  };

  // List View Component
  const MeetingsListView = () => (
    <div className="space-y-6">
      {/* Header with Actions */}
      <div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">議事録管理</h1>
          <p className="text-muted-foreground">
            Google Meet議事録の管理と構造化データ抽出
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            onClick={handleCollectMeetings}
            disabled={collecting}
            className="flex items-center space-x-2"
          >
            {collecting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            <span>{collecting ? "取得中..." : "Google Driveから取得"}</span>
          </Button>
          
          <Button
            variant="outline"
            size="icon"
            onClick={loadMeetings}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Search and Filter Controls */}
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
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
        </CardContent>
      </Card>


      {/* Meetings Tabs */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="all">全て ({filteredMeetings.length})</TabsTrigger>
          <TabsTrigger value="structured">構造化済み ({structuredMeetings.length})</TabsTrigger>
          <TabsTrigger value="unstructured">未処理 ({unstructuredMeetings.length})</TabsTrigger>
        </TabsList>
        
        <TabsContent value="all" className="space-y-4">
          <MeetingsList meetings={filteredMeetings} />
        </TabsContent>
        
        <TabsContent value="structured" className="space-y-4">
          <MeetingsList meetings={structuredMeetings} />
        </TabsContent>
        
        <TabsContent value="unstructured" className="space-y-4">
          <MeetingsList meetings={unstructuredMeetings} />
        </TabsContent>
      </Tabs>
    </div>
  );

  // Meetings List Component
  const MeetingsList = ({ meetings }: { meetings: Meeting[] }) => {
    if (loading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">読み込み中...</p>
          </div>
        </div>
      );
    }

    if (meetings.length === 0) {
      return (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium text-muted-foreground mb-2">議事録が見つかりません</h3>
            <p className="text-sm text-muted-foreground mb-4">Google Driveから議事録を取得してください</p>
            <Button onClick={handleCollectMeetings} disabled={collecting}>
              {collecting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}
              {collecting ? "取得中..." : "Google Driveから取得"}
            </Button>
          </CardContent>
        </Card>
      );
    }

    return (
      <div className="space-y-3">
        {meetings.map((meeting) => (
          <Card key={meeting.id} className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => handleMeetingSelect(meeting)}>
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-lg font-medium truncate">
                      {meeting.title || '(無題)'}
                    </h3>
                    <Badge variant={structuredMeetings.some(m => m.id === meeting.id) ? "default" : "secondary"}>
                      {structuredMeetings.some(m => m.id === meeting.id) ? "構造化済み" : "未処理"}
                    </Badge>
                  </div>
                  
                  <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                    <div className="flex items-center space-x-1">
                      <User className="h-4 w-4" />
                      <span>{meeting.organizer_email}</span>
                    </div>
                    {meeting.meeting_datetime && (
                      <div className="flex items-center space-x-1">
                        <Clock className="h-4 w-4" />
                        <span>{formatDateTime(meeting.meeting_datetime)}</span>
                      </div>
                    )}
                    <div className="flex items-center space-x-1">
                      <Users className="h-4 w-4" />
                      <span>{meeting.invited_emails.length}名参加</span>
                    </div>
                  </div>
                </div>
                
                <ChevronRight className="h-5 w-5 text-muted-foreground ml-4" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  };

  // Detail View Component
  const MeetingDetailView = () => {
    if (!selectedMeeting) return null;

    return (
      <div className="space-y-6">
        {/* Header with Back Button */}
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="sm" onClick={handleBackToList}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            議事録一覧に戻る
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold truncate">{selectedMeeting.title || '(無題)'}</h1>
            <p className="text-muted-foreground">議事録の詳細情報と構造化処理</p>
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
                  <div className="flex items-center space-x-1">
                    <Mail className="h-4 w-4" />
                    <span>{selectedMeeting.organizer_email}</span>
                  </div>
                  {selectedMeeting.meeting_datetime && (
                    <div className="flex items-center space-x-1">
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
                    <Badge key={index} variant="outline">
                      {email}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          )}
        </Card>

        {/* Content Area */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Processing Section */}
          <div className="space-y-6">
            {loadingStructured ? (
              <Card>
                <CardContent className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
                    <p className="text-muted-foreground">構造化データを確認中...</p>
                  </div>
                </CardContent>
              </Card>
            ) : structuredData && structuredData.data && Object.keys(structuredData.data).length > 0 ? (
              <StructuredDataCard data={structuredData} />
            ) : (
              <CandidateSelectionCard />
            )}
          </div>

          {/* Preview Section */}
          <div className="space-y-6">
            {selectedMeeting.text_content && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Eye className="h-5 w-5" />
                    <span>議事録プレビュー</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-96 w-full rounded-md border p-4">
                    <pre className="whitespace-pre-wrap text-sm">
                      {selectedMeeting.text_content}
                    </pre>
                  </ScrollArea>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    );
  };

  const StructuredDataCard = ({ data }: { data: StructuredData }) => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Sparkles className="h-5 w-5 text-green-600" />
          <span>構造化出力</span>
        </CardTitle>
        <CardDescription>
          AI による議事録の構造化データ抽出結果
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {data.zoho_candidate && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <h4 className="font-medium mb-2 text-green-800">対応求職者</h4>
            <div className="text-sm space-y-1">
              <div><strong>名前:</strong> {data.zoho_candidate.candidate_name}</div>
              <div><strong>ID:</strong> {data.zoho_candidate.candidate_id}</div>
              {data.zoho_candidate.candidate_email && (
                <div><strong>メール:</strong> {data.zoho_candidate.candidate_email}</div>
              )}
            </div>
          </div>
        )}
        
        <div className="space-y-3">
          {Object.entries(data.data).map(([key, value]) => (
            <div key={key} className="flex flex-col space-y-1 pb-3 border-b">
              <div className="text-sm font-medium text-muted-foreground">
                {key.replace(/_/g, ' ')}
              </div>
              <div className="text-sm">
                {Array.isArray(value) ? value.join(', ') : String(value || '-')}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );

  const CandidateSelectionCard = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <UserCheck className="h-5 w-5" />
          <span>求職者の選択</span>
        </CardTitle>
        <CardDescription>
          構造化処理を行う前に、対応する求職者を選択してください
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
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{suggestion.candidate.candidate_name}</div>
                        <div className="text-sm text-muted-foreground">
                          ID: {suggestion.candidate.candidate_id}
                        </div>
                      </div>
                      <Badge variant={suggestion.confidence > 0.7 ? "default" : "secondary"}>
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
        <Separator />
        <Button 
          onClick={handleProcessStructured}
          disabled={!selectedCandidate || processing}
          className="w-full"
          size="lg"
        >
          {processing ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              構造化処理中...
            </>
          ) : selectedCandidate ? (
            <>
              <Sparkles className="h-4 w-4 mr-2" />
              {selectedCandidate.candidate_name} で構造化処理を実行
            </>
          ) : (
            <>
              <AlertCircle className="h-4 w-4 mr-2" />
              候補者を選択してください
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );

  return (
    <ModernAppShell activeTab="hitocari">
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        {viewMode === 'list' ? <MeetingsListView /> : <MeetingDetailView />}
      </div>

      {/* Candidate Search Dialog */}
      <CandidateSearchDialog
        open={showCandidateSearch}
        onOpenChange={setShowCandidateSearch}
        onCandidateSelect={setSelectedCandidate}
        selectedCandidate={selectedCandidate}
      />
    </ModernAppShell>
  );
}