"use client";

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
  Clock,
  PieChart,
} from "lucide-react";
import Link from "next/link";
import { SidebarTrigger } from "@/components/ui/sidebar";

export default function Dashboard() {
  return (
    <>
      <div className="container mx-auto px-6 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-2">
            <SidebarTrigger className="md:hidden" />
            <h1 className="text-3xl font-bold">b&q Hub ダッシュボード</h1>
          </div>
          <p className="text-muted-foreground">
            統合管理システムへようこそ。各サービスにアクセスして業務を効率化しましょう。
          </p>
        </div>

        {/* Service Cards */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-8">
          {/* ひとキャリ Card */}
          <Card className="relative overflow-hidden border-2 border-primary/10 bg-gradient-to-br from-[#a3d8e2]/40 via-[#79c5d8]/20 to-transparent">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg text-primary-foreground bg-[linear-gradient(135deg,var(--brand-300),var(--brand-400))]">
                  <Users className="w-6 h-6" />
                </div>
                <Badge variant="default">
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

          {/* マーケティング AI Card */}
          <Card className="relative overflow-hidden border border-primary/20 bg-white shadow-sm">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                  <PieChart className="w-6 h-6" />
                </div>
                <Badge>
                  New
                </Badge>
              </div>
              <CardTitle className="text-xl">マーケティング AI</CardTitle>
              <CardDescription>
                Ahrefs / GSC / GA4 / Web検索を束ねたChatKitチャット
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <TrendingUp className="w-4 h-4" />
                <span>SEOリサーチ自動化</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FileText className="w-4 h-4" />
                <span>ProgressUpdateEventで推論可視化</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Search className="w-4 h-4" />
                <span>Supabaseに会話ログ保存</span>
              </div>
              <Button asChild className="w-full mt-4" variant="secondary">
                <Link href="/marketing" className="flex items-center gap-2">
                  チャットを開く
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
    </>
  );
}
