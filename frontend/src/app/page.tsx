"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { AppShell } from "@/components/app-shell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Users, 
  Building2, 
  Briefcase, 
  ArrowRight,
  FileText,
  Search,
  TrendingUp,
  Clock
} from "lucide-react";
import Link from "next/link";

export default function Dashboard() {
  const { isLoaded, userId } = useAuth();
  const { user } = useUser();
  const router = useRouter();

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

  return (
    <AppShell activeTab="dashboard">
      <div className="container mx-auto px-6 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">b&q Hub ダッシュボード</h1>
          <p className="text-muted-foreground">
            統合管理システムへようこそ。各サービスにアクセスして業務を効率化しましょう。
          </p>
        </div>

        {/* Service Cards */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-8">
          {/* ひとキャリ Card */}
          <Card className="relative overflow-hidden border-2 border-primary/20 bg-gradient-to-br from-blue-50 to-indigo-50">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Users className="w-6 h-6 text-primary" />
                </div>
                <Badge variant="default" className="bg-primary">
                  利用可能
                </Badge>
              </div>
              <CardTitle className="text-xl">ひとキャリ</CardTitle>
              <CardDescription>
                Google Meet議事録の管理と構造化データ抽出
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FileText className="w-4 h-4" />
                <span>議事録管理</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Search className="w-4 h-4" />
                <span>Zoho CRM連携</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <TrendingUp className="w-4 h-4" />
                <span>AI構造化抽出</span>
              </div>
              <Button asChild className="w-full mt-4">
                <Link href="/hitocari" className="flex items-center gap-2">
                  開始する
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* モノテック Card */}
          <Card className="relative overflow-hidden opacity-75">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-muted rounded-lg">
                  <Building2 className="w-6 h-6 text-muted-foreground" />
                </div>
                <Badge variant="outline">
                  準備中
                </Badge>
              </div>
              <CardTitle className="text-xl text-muted-foreground">モノテック</CardTitle>
              <CardDescription>
                技術系人材サービス管理システム
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="w-4 h-4" />
                <span>近日公開予定</span>
              </div>
              <Button disabled className="w-full mt-4">
                準備中
              </Button>
            </CardContent>
          </Card>

          {/* AchieveHR Card */}
          <Card className="relative overflow-hidden opacity-75">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-muted rounded-lg">
                  <Briefcase className="w-6 h-6 text-muted-foreground" />
                </div>
                <Badge variant="outline">
                  準備中
                </Badge>
              </div>
              <CardTitle className="text-xl text-muted-foreground">AchieveHR</CardTitle>
              <CardDescription>
                人事・採用統合管理システム
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="w-4 h-4" />
                <span>近日公開予定</span>
              </div>
              <Button disabled className="w-full mt-4">
                準備中
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              クイックアクション
            </CardTitle>
            <CardDescription>
              よく使用される機能への素早いアクセス
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Button asChild variant="outline" className="h-auto p-4">
                <Link href="/hitocari" className="flex flex-col items-center gap-2">
                  <FileText className="w-6 h-6" />
                  <div className="text-center">
                    <div className="font-medium">議事録管理</div>
                    <div className="text-xs text-muted-foreground">ひとキャリ</div>
                  </div>
                </Link>
              </Button>
              
              <Button variant="outline" disabled className="h-auto p-4 opacity-50">
                <div className="flex flex-col items-center gap-2">
                  <Search className="w-6 h-6" />
                  <div className="text-center">
                    <div className="font-medium">候補者検索</div>
                    <div className="text-xs text-muted-foreground">準備中</div>
                  </div>
                </div>
              </Button>
              
              <Button variant="outline" disabled className="h-auto p-4 opacity-50">
                <div className="flex flex-col items-center gap-2">
                  <TrendingUp className="w-6 h-6" />
                  <div className="text-center">
                    <div className="font-medium">分析</div>
                    <div className="text-xs text-muted-foreground">準備中</div>
                  </div>
                </div>
              </Button>
              
              <Button variant="outline" disabled className="h-auto p-4 opacity-50">
                <div className="flex flex-col items-center gap-2">
                  <Users className="w-6 h-6" />
                  <div className="text-center">
                    <div className="font-medium">チーム管理</div>
                    <div className="text-xs text-muted-foreground">準備中</div>
                  </div>
                </div>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
