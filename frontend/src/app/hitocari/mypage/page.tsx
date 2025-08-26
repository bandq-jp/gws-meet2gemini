"use client";

import { useState, useEffect, useMemo } from "react";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  FileText,
  Clock,
  User,
  Users,
  ChevronRight,
  Calendar,
  TrendingUp,
  Loader2,
} from "lucide-react";
import { 
  apiClient, 
  MeetingSummary,
} from "@/lib/api";
import { formatDistanceToNow, parseISO, isToday, format } from "date-fns";
import { ja } from "date-fns/locale";

export default function MyPage() {
  const { user } = useUser();
  const [meetings, setMeetings] = useState<MeetingSummary[]>([]);
  const [loading, setLoading] = useState(true);

  // Load user's meetings
  const loadMyMeetings = async () => {
    try {
      setLoading(true);
      
      if (!user?.emailAddresses?.[0]?.emailAddress) {
        return;
      }

      const userEmail = user.emailAddresses[0].emailAddress;
      
      // Load recent meetings for the current user (max 40 per API limit)
      const data = await apiClient.getMeetings(1, 40, [userEmail]);
      setMeetings(data.items);
      
    } catch (error: unknown) {
      console.error('Failed to load my meetings:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.emailAddresses?.[0]?.emailAddress) {
      loadMyMeetings();
    }
  }, [user?.emailAddresses]);

  // Filter meetings by date
  const { todayMeetings, recentMeetings } = useMemo(() => {
    const today: MeetingSummary[] = [];
    const recent: MeetingSummary[] = [];

    for (const meeting of meetings) {
      if (meeting.meeting_datetime) {
        try {
          const meetingDate = parseISO(meeting.meeting_datetime);
          
          if (isToday(meetingDate)) {
            today.push(meeting);
          } else {
            recent.push(meeting);
          }
        } catch {
          // If date parsing fails, add to recent
          recent.push(meeting);
        }
      } else {
        recent.push(meeting);
      }
    }

    // Sort by most recent first
    today.sort((a, b) => new Date(b.meeting_datetime || 0).getTime() - new Date(a.meeting_datetime || 0).getTime());
    recent.sort((a, b) => new Date(b.meeting_datetime || 0).getTime() - new Date(a.meeting_datetime || 0).getTime());

    // Limit recent meetings to 6 items
    return {
      todayMeetings: today,
      recentMeetings: recent.slice(0, 6)
    };
  }, [meetings]);

  const formatDateTime = (dateString: string) => {
    try {
      const date = parseISO(dateString);
      return formatDistanceToNow(date, { addSuffix: true, locale: ja });
    } catch {
      return dateString;
    }
  };

  const formatDateOnly = (dateString: string) => {
    try {
      const date = parseISO(dateString);
      return format(date, 'M月d日', { locale: ja });
    } catch {
      return dateString;
    }
  };

  // Meeting Card Component
  const MeetingCard = ({ meeting }: { meeting: MeetingSummary }) => (
    <Link key={meeting.id} href={`/hitocari/${meeting.id}`}>
      <Card className="hover:shadow-md transition-all duration-200 cursor-pointer active:scale-[0.98] transform">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0 space-y-2">
              <div className="flex items-start justify-between">
                <h3 className="text-sm font-medium line-clamp-2 flex-1 mr-2">
                  {meeting.title || '(無題)'}
                </h3>
                <Badge 
                  variant={meeting.is_structured ? "default" : "secondary"}
                  className="text-xs px-2 py-0.5 shrink-0"
                >
                  {meeting.is_structured ? "構造化済" : "未処理"}
                </Badge>
              </div>
              
              <div className="flex items-center space-x-3 text-xs text-muted-foreground">
                {meeting.meeting_datetime && (
                  <div className="flex items-center space-x-1">
                    <Clock className="h-3 w-3" />
                    <span>{formatDateTime(meeting.meeting_datetime)}</span>
                  </div>
                )}
                <div className="flex items-center space-x-1">
                  <Users className="h-3 w-3" />
                  <span>{meeting.invited_emails.length}名</span>
                </div>
              </div>
            </div>
            
            <ChevronRight className="h-4 w-4 text-muted-foreground ml-2 shrink-0" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );

  if (loading) {
    return (
      <div className="w-full px-3 py-4 sm:px-6 sm:py-6">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">読み込み中...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full px-3 py-4 sm:px-6 sm:py-6">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center space-x-2 sm:space-x-4">
          <SidebarTrigger className="md:hidden" />
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">マイページ</h1>
            <p className="text-sm sm:text-base text-muted-foreground">
              {user?.fullName || user?.emailAddresses?.[0]?.emailAddress?.split('@')[0]}さんの議事録
            </p>
          </div>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">総議事録数</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{meetings.length}</div>
              <p className="text-xs text-muted-foreground">
                全ての議事録
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">今日の議事録</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{todayMeetings.length}</div>
              <p className="text-xs text-muted-foreground">
                本日開催
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">構造化済み</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {meetings.filter(m => m.is_structured).length}
              </div>
              <p className="text-xs text-muted-foreground">
                処理済み議事録
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Today's Meetings */}
        {todayMeetings.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Calendar className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-semibold">今日の議事録</h2>
              <Badge variant="secondary">{todayMeetings.length}件</Badge>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {todayMeetings.map((meeting) => (
                <MeetingCard key={meeting.id} meeting={meeting} />
              ))}
            </div>
          </div>
        )}

        {/* Recent Meetings */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Clock className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-semibold">
                {todayMeetings.length > 0 ? '過去の議事録' : '議事録一覧'}
              </h2>
              <Badge variant="secondary">{recentMeetings.length}件</Badge>
            </div>
            {recentMeetings.length >= 6 && (
              <Link 
                href="/hitocari" 
                className="text-sm text-primary hover:underline flex items-center space-x-1"
              >
                <span>すべて見る</span>
                <ChevronRight className="h-3 w-3" />
              </Link>
            )}
          </div>

          {recentMeetings.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {recentMeetings.map((meeting) => (
                <MeetingCard key={meeting.id} meeting={meeting} />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium text-muted-foreground mb-2">
                  議事録がありません
                </h3>
                <p className="text-sm text-muted-foreground text-center">
                  まだ議事録が作成されていないか、<br />
                  あなたが参加した会議がありません。
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}