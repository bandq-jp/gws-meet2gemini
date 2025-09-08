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
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
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
  Check,
  ChevronsUpDown,
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
  
  // Combobox states
  const [open, setOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<string>("");

  // Load available accounts function
  const loadAvailableAccounts = async () => {
    try {
      const response = await apiClient.getAvailableAccounts();
      setAvailableAccounts(response.accounts);
      
      // ローカルストレージから保存された設定を復元
      const savedShowAllAccounts = localStorage.getItem('hitocari-showAllAccounts');
      const savedCurrentUserEmail = localStorage.getItem('hitocari-currentUserEmail');
      
      if (savedShowAllAccounts !== null) {
        const isShowAll = savedShowAllAccounts === 'true';
        setShowAllAccounts(isShowAll);
        
        if (isShowAll) {
          setSelectedAccount("all");
          setCurrentUserEmail("");
        } else if (savedCurrentUserEmail && response.accounts.includes(savedCurrentUserEmail)) {
          setCurrentUserEmail(savedCurrentUserEmail);
          setSelectedAccount(savedCurrentUserEmail);
        } else if (response.accounts.length > 0) {
          // 保存されたアカウントが無い場合は最初のアカウントを使用
          setCurrentUserEmail(response.accounts[0]);
          setSelectedAccount(response.accounts[0]);
        }
      } else {
        // 初回設定：最初のアカウントをデフォルトに
        if (response.accounts.length > 0) {
          setCurrentUserEmail(response.accounts[0]);
          setSelectedAccount(response.accounts[0]);
          setShowAllAccounts(false);
        }
      }
    } catch (error) {
      console.error('Failed to load available accounts:', error);
      setAvailableAccounts([]);
    }
  };

  // アカウントオプションの作成
  const accountOptions = [
    { value: "all", label: "全アカウント" },
    ...availableAccounts.map(email => ({
      value: email,
      label: email.split('@')[0]
    }))
  ];

  // アカウント選択の処理
  const handleAccountSelect = (value: string) => {
    if (value === "all") {
      setShowAllAccounts(true);
      setCurrentUserEmail("");
      localStorage.setItem('hitocari-showAllAccounts', 'true');
      localStorage.removeItem('hitocari-currentUserEmail');
    } else {
      setShowAllAccounts(false);
      setCurrentUserEmail(value);
      localStorage.setItem('hitocari-showAllAccounts', 'false');
      localStorage.setItem('hitocari-currentUserEmail', value);
    }
    setSelectedAccount(value);
    setOpen(false);
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


  // Load meetings and accounts on component mount
  useEffect(() => {
    loadAvailableAccounts();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // selectedAccountの状態をショートカットで更新するためのuseEffect
  useEffect(() => {
    if (availableAccounts.length > 0) {
      if (showAllAccounts) {
        setSelectedAccount("all");
      } else if (currentUserEmail) {
        setSelectedAccount(currentUserEmail);
      }
    }
  }, [showAllAccounts, currentUserEmail, availableAccounts]);

  // Load meetings when accounts or filters change
  useEffect(() => {
    if (availableAccounts.length > 0) {
      loadMeetings(activeTab, getCurrentPage(), true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showAllAccounts, currentUserEmail, activeTab, availableAccounts.length]);


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
      <div className="flex flex-col space-y-3 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
        <div className="text-xs sm:text-sm text-muted-foreground text-center sm:text-left">
          ページ {currentPage} / {total_pages}
        </div>
        <div className="flex items-center justify-center space-x-1 sm:space-x-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!has_previous || loading}
            onClick={() => handlePageChange(currentPage - 1)}
            className="text-xs sm:text-sm px-2 sm:px-3"
          >
            前へ
          </Button>
          
          <div className="flex items-center space-x-1">
            {Array.from({ length: Math.min(3, total_pages) }, (_, i) => {
              const pageNum = Math.max(1, Math.min(total_pages - 2, currentPage - 1)) + i;
              if (pageNum <= total_pages) {
                return (
                  <Button
                    key={pageNum}
                    variant={pageNum === currentPage ? "default" : "outline"}
                    size="sm"
                    disabled={loading}
                    onClick={() => handlePageChange(pageNum)}
                    className="w-8 h-8 text-xs sm:text-sm p-0"
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
            className="text-xs sm:text-sm px-2 sm:px-3"
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
      <div className="space-y-2 sm:space-y-3">
        {meetings.map((meeting) => (
          <Link key={meeting.id} href={`/hitocari/${meeting.id}`}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer active:scale-[0.98] transition-transform">
              <CardContent className="p-4 sm:p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex flex-col space-y-2 sm:flex-row sm:items-center sm:space-y-0 sm:space-x-2">
                      <h3 className="text-base sm:text-lg font-medium line-clamp-2 sm:truncate">
                        {meeting.title || '(無題)'}
                      </h3>
                      <Badge 
                        variant={meeting.is_structured ? "default" : "secondary"}
                        className="self-start sm:self-auto text-xs px-2 py-0.5"
                      >
                        {meeting.is_structured ? "構造化済" : "未処理"}
                      </Badge>
                    </div>
                    
                    <div className="space-y-1 sm:space-y-0 sm:flex sm:items-center sm:space-x-4 text-xs sm:text-sm text-muted-foreground">
                      <div className="flex items-center space-x-1 min-w-0">
                        <User className="h-3 w-3 sm:h-4 sm:w-4 shrink-0" />
                        <span className="truncate">{meeting.organizer_email?.split('@')[0] || meeting.organizer_email}</span>
                      </div>
                      {meeting.meeting_datetime && (
                        <div className="flex items-center space-x-1">
                          <Clock className="h-3 w-3 sm:h-4 sm:w-4 shrink-0" />
                          <span className="truncate">{formatDateTime(meeting.meeting_datetime)}</span>
                        </div>
                      )}
                      <div className="flex items-center space-x-1">
                        <Users className="h-3 w-3 sm:h-4 sm:w-4 shrink-0" />
                        <span>{meeting.invited_emails.length}名</span>
                      </div>
                    </div>
                  </div>
                  
                  <ChevronRight className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground ml-2 sm:ml-4 shrink-0" />
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    );
  };

  return (
    <div className="w-full px-3 py-4 sm:px-6 sm:py-6">
      <div className="space-y-4 sm:space-y-6">
        {/* Header with Actions */}
        <div className="flex flex-col space-y-3 sm:space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
          <div className="flex items-center space-x-2 sm:space-x-4">
            <SidebarTrigger className="md:hidden" />
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">議事録管理 -Beta版-</h1>
              <p className="text-sm sm:text-base text-muted-foreground hidden sm:block">
                Google Meet議事録の管理と構造化データ抽出
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2 sm:space-x-2 w-full sm:w-auto">
            <Button
              onClick={handleCollectMeetings}
              disabled={collecting}
              className="flex-1 sm:flex-none items-center justify-center"
              size="sm"
            >
              {collecting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              <span className="ml-2 sm:ml-2">{collecting ? "取得中" : "取得"}</span>
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadMeetings()}
              disabled={loading}
              className="px-3"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* Search and Filter Controls */}
        <Card>
          <CardContent className="p-3 sm:p-6">
            <div className="space-y-3 sm:space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="タイトル、主催者で検索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 text-base sm:text-sm"
                />
              </div>
              
              <div className="flex flex-col space-y-3 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
                <div className="flex items-center space-x-3">
                  <Label className="text-sm hidden sm:block">
                    アカウント:
                  </Label>
                  <Popover open={open} onOpenChange={setOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={open}
                        className="w-[200px] justify-between text-xs sm:text-sm"
                      >
                        {selectedAccount
                          ? accountOptions.find((option) => option.value === selectedAccount)?.label
                          : "アカウントを選択..."}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[200px] p-0">
                      <Command>
                        <CommandInput placeholder="アカウントを検索..." />
                        <CommandList>
                          <CommandEmpty>アカウントが見つかりません</CommandEmpty>
                          <CommandGroup>
                            {accountOptions.map((option) => (
                              <CommandItem
                                key={option.value}
                                value={option.value}
                                onSelect={() => handleAccountSelect(option.value)}
                              >
                                <Check
                                  className={`mr-2 h-4 w-4 ${
                                    selectedAccount === option.value ? "opacity-100" : "opacity-0"
                                  }`}
                                />
                                {option.label}
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>
                
                {meetingsResponse && (
                  <div className="text-xs sm:text-sm text-muted-foreground text-right">
                    <div className="sm:hidden">
                      {meetingsResponse.total}件
                    </div>
                    <div className="hidden sm:block">
                      {meetingsResponse.total}件中 {((meetingsResponse.page - 1) * meetingsResponse.page_size) + 1}-{Math.min(meetingsResponse.page * meetingsResponse.page_size, meetingsResponse.total)}件を表示
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Meetings Tabs */}
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="space-y-3 sm:space-y-4">
          <TabsList className="grid w-full grid-cols-3 h-auto">
            <TabsTrigger value="all" className="text-xs sm:text-sm py-2 px-1 sm:px-3">
              <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-1">
                <span>全て</span>
                {meetingsResponse && activeTab === 'all' && (
                  <span className="text-xs sm:text-sm">({meetingsResponse.total})</span>
                )}
              </div>
            </TabsTrigger>
            <TabsTrigger value="structured" className="text-xs sm:text-sm py-2 px-1 sm:px-3">
              <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-1">
                <span>構造化</span>
                {meetingsResponse && activeTab === 'structured' && (
                  <span className="text-xs sm:text-sm">({meetingsResponse.total})</span>
                )}
              </div>
            </TabsTrigger>
            <TabsTrigger value="unstructured" className="text-xs sm:text-sm py-2 px-1 sm:px-3">
              <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-1">
                <span>未処理</span>
                {meetingsResponse && activeTab === 'unstructured' && (
                  <span className="text-xs sm:text-sm">({meetingsResponse.total})</span>
                )}
              </div>
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