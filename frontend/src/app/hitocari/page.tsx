"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import {
  Download,
  Search,
  RefreshCw,
  FileText,
  Clock,
  User,
  Loader2,
  Users,
  ChevronRight,
} from "lucide-react";
import { 
  apiClient, 
  MeetingSummary,
  MeetingListResponse,
} from "@/lib/api";
import { formatDistanceToNow, parseISO } from "date-fns";
import { ja } from "date-fns/locale";
import toast from "react-hot-toast";
import { SidebarTrigger } from "@/components/ui/sidebar";

export default function HitocariListPage() {
  // Meeting list states
  const [meetingsResponse, setMeetingsResponse] = useState<MeetingListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [availableAccounts, setAvailableAccounts] = useState<string[]>([]);
  const [showAllAccounts, setShowAllAccounts] = useState(false);
  const [currentUserEmail, setCurrentUserEmail] = useState<string>("");
  
  // Pagination states
  const [allPage, setAllPage] = useState(1);
  const [structuredPage, setStructuredPage] = useState(1);
  const [unstructuredPage, setUnstructuredPage] = useState(1);
  
  // Tab states
  const [activeTab, setActiveTab] = useState<'all' | 'structured' | 'unstructured'>('all');

  // Load available accounts function
  const loadAvailableAccounts = async () => {
    try {
      const response = await apiClient.getAvailableAccounts();
      setAvailableAccounts(response.accounts);
      if (response.accounts.length > 0 && !currentUserEmail) {
        setCurrentUserEmail(response.accounts[0]); // デフォルトは最初のアカウント
      }
    } catch (error) {
      console.error('Failed to load available accounts:', error);
      setAvailableAccounts([]);
    }
  };

  // Define loadMeetings function for paginated data
  const loadMeetings = async (
    tab: 'all' | 'structured' | 'unstructured' = activeTab,
    page: number = 1,
    resetPage: boolean = false
  ) => {
    try {
      setLoading(true);
      
      const accounts = showAllAccounts ? undefined : (currentUserEmail ? [currentUserEmail] : undefined);
      const structured = tab === 'all' ? undefined : (tab === 'structured');
      
      const data = await apiClient.getMeetings(page, 40, accounts, structured);
      setMeetingsResponse(data);
      
      // ページリセットが必要な場合
      if (resetPage) {
        setAllPage(1);
        setStructuredPage(1);
        setUnstructuredPage(1);
      }
      
    } catch (error: unknown) {
      console.error('Failed to load meetings:', error);
      const errorMessage = error instanceof Error ? error.message : '不明なエラー';
      toast.error(`議事録の読み込みに失敗しました: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  // 検索フィルタ済みのミーティング（軽量検索のみ）
  const filteredMeetings = useMemo(() => {
    if (!meetingsResponse?.items) return [];
    
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      return meetingsResponse.items.filter(meeting =>
        meeting.title?.toLowerCase().includes(query) ||
        meeting.organizer_email?.toLowerCase().includes(query) ||
        meeting.invited_emails?.some(email => email.toLowerCase().includes(query))
      );
    }

    return meetingsResponse.items;
  }, [meetingsResponse, searchQuery]);

  // 現在のページ番号を取得
  const getCurrentPage = () => {
    switch (activeTab) {
      case 'structured': return structuredPage;
      case 'unstructured': return unstructuredPage;
      default: return allPage;
    }
  };

  // ページ変更ハンドラ
  const handlePageChange = (newPage: number) => {
    switch (activeTab) {
      case 'structured':
        setStructuredPage(newPage);
        break;
      case 'unstructured':
        setUnstructuredPage(newPage);
        break;
      default:
        setAllPage(newPage);
        break;
    }
    loadMeetings(activeTab, newPage);
  };

  // ローカルストレージからアカウントフィルタ設定を読み込み
  useEffect(() => {
    const savedShowAllAccounts = localStorage.getItem('hitocari-showAllAccounts');
    if (savedShowAllAccounts !== null) {
      setShowAllAccounts(savedShowAllAccounts === 'true');
    }
  }, []);

  // Load meetings and accounts on component mount
  useEffect(() => {
    loadAvailableAccounts();
  }, []);

  // Load meetings when accounts or filters change
  useEffect(() => {
    if (availableAccounts.length > 0) {
      loadMeetings(activeTab, getCurrentPage(), true);
    }
  }, [showAllAccounts, currentUserEmail, activeTab]);

  // アカウントフィルタ切り替え
  const toggleAccountFilter = () => {
    const newValue = !showAllAccounts;
    setShowAllAccounts(newValue);
    // ローカルストレージに保存
    localStorage.setItem('hitocari-showAllAccounts', String(newValue));
  };

  const handleCollectMeetings = async () => {
    try {
      setCollecting(true);
      const accounts = showAllAccounts ? undefined : (currentUserEmail ? [currentUserEmail] : undefined);
      const result = await apiClient.collectMeetings(accounts, false, false);
      
      await loadMeetings(activeTab, getCurrentPage(), true);
      
      toast.success(`${result.stored}件の議事録を取得しました`);
    } catch (error: unknown) {
      console.error('Failed to collect meetings:', error);
      const errorMessage = error instanceof Error ? error.message : '不明なエラー';
      toast.error(`議事録の取得に失敗しました: ${errorMessage}`);
    } finally {
      setCollecting(false);
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

  // Pagination Controls Component
  const PaginationControls = () => {
    if (!meetingsResponse || meetingsResponse.total_pages <= 1) return null;
    
    const currentPage = getCurrentPage();
    const { total_pages, has_previous, has_next } = meetingsResponse;
    
    return (
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          ページ {currentPage} / {total_pages}
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!has_previous || loading}
            onClick={() => handlePageChange(currentPage - 1)}
          >
            前へ
          </Button>
          
          <div className="flex items-center space-x-1">
            {Array.from({ length: Math.min(5, total_pages) }, (_, i) => {
              const pageNum = Math.max(1, Math.min(total_pages - 4, currentPage - 2)) + i;
              if (pageNum <= total_pages) {
                return (
                  <Button
                    key={pageNum}
                    variant={pageNum === currentPage ? "default" : "outline"}
                    size="sm"
                    disabled={loading}
                    onClick={() => handlePageChange(pageNum)}
                    className="w-8"
                  >
                    {pageNum}
                  </Button>
                );
              }
              return null;
            })}
          </div>
          
          <Button
            variant="outline"
            size="sm"
            disabled={!has_next || loading}
            onClick={() => handlePageChange(currentPage + 1)}
          >
            次へ
          </Button>
        </div>
      </div>
    );
  };

  // Meetings List Component
  const MeetingsList = ({ meetings }: { meetings: MeetingSummary[] }) => {
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
          <Link key={meeting.id} href={`/hitocari/${meeting.id}`}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-medium truncate">
                        {meeting.title || '(無題)'}
                      </h3>
                      <Badge variant={meeting.is_structured ? "default" : "secondary"}>
                        {meeting.is_structured ? "構造化済み" : "未処理"}
                      </Badge>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-muted-foreground overflow-hidden">
                      <div className="flex items-center space-x-1 min-w-0">
                        <User className="h-4 w-4 shrink-0" />
                        <span className="truncate">{meeting.organizer_email}</span>
                      </div>
                      {meeting.meeting_datetime && (
                        <div className="flex items-center space-x-1 shrink-0">
                          <Clock className="h-4 w-4" />
                          <span>{formatDateTime(meeting.meeting_datetime)}</span>
                        </div>
                      )}
                      <div className="flex items-center space-x-1 shrink-0">
                        <Users className="h-4 w-4" />
                        <span>{meeting.invited_emails.length}名参加</span>
                      </div>
                    </div>
                  </div>
                  
                  <ChevronRight className="h-5 w-5 text-muted-foreground ml-4" />
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    );
  };

  return (
    <div className="w-full px-6 py-6">
      <div className="space-y-6">
        {/* Header with Actions */}
        <div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
          <div className="flex items-center space-x-4">
            <SidebarTrigger className="md:hidden" />
            <div>
              <h1 className="text-3xl font-bold tracking-tight">議事録管理</h1>
              <p className="text-muted-foreground">
                Google Meet議事録の管理と構造化データ抽出
              </p>
            </div>
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
              onClick={() => loadMeetings()}
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
                  placeholder="議事録を検索（タイトル、主催者、参加者）..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Label htmlFor="account-filter" className="text-sm">
                    アカウントフィルタ:
                  </Label>
                  <div className="flex items-center space-x-3">
                    <span className={`text-sm ${!showAllAccounts ? 'font-medium' : 'text-muted-foreground'}`}>
                      {currentUserEmail || 'マイアカウント'}
                    </span>
                    <Switch
                      id="account-filter"
                      checked={showAllAccounts}
                      onCheckedChange={toggleAccountFilter}
                    />
                    <span className={`text-sm ${showAllAccounts ? 'font-medium' : 'text-muted-foreground'}`}>
                      全てのアカウント
                    </span>
                  </div>
                </div>
                
                {meetingsResponse && (
                  <div className="text-sm text-muted-foreground">
                    {meetingsResponse.total}件中 {((meetingsResponse.page - 1) * meetingsResponse.page_size) + 1}-{Math.min(meetingsResponse.page * meetingsResponse.page_size, meetingsResponse.total)}件を表示
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Meetings Tabs */}
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="all">
              全て {meetingsResponse && activeTab === 'all' ? `(${meetingsResponse.total})` : ''}
            </TabsTrigger>
            <TabsTrigger value="structured">
              構造化済み {meetingsResponse && activeTab === 'structured' ? `(${meetingsResponse.total})` : ''}
            </TabsTrigger>
            <TabsTrigger value="unstructured">
              未処理 {meetingsResponse && activeTab === 'unstructured' ? `(${meetingsResponse.total})` : ''}
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="all" className="space-y-4">
            <MeetingsList meetings={filteredMeetings} />
            <PaginationControls />
          </TabsContent>
          
          <TabsContent value="structured" className="space-y-4">
            <MeetingsList meetings={filteredMeetings} />
            <PaginationControls />
          </TabsContent>
          
          <TabsContent value="unstructured" className="space-y-4">
            <MeetingsList meetings={filteredMeetings} />
            <PaginationControls />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}