import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  ExternalLink,
  Link as LinkIcon,
} from "lucide-react";

const kpis = [
  {
    label: "自然検索セッション (30日)",
    value: "128,420",
    change: 12.4,
  },
  {
    label: "マーケ起点CV", 
    value: "842",
    change: 8.1,
  },
  {
    label: "SQLパイプライン",
    value: "¥46.2M",
    change: 5.6,
  },
  {
    label: "平均検索順位",
    value: "8.4位",
    change: -0.7,
  },
];

const channelBreakdown = [
  { name: "Ahrefs オーガニック", sessions: 64200, trend: 9.3 },
  { name: "GSC ブランド", sessions: 28100, trend: 3.8 },
  { name: "GSC ノンブランド", sessions: 20450, trend: 11.2 },
  { name: "GA4 リターゲティング", sessions: 15700, trend: -2.4 },
];

const keywordInsights = [
  {
    keyword: "転職 コンサルタント",
    volume: "6.6K",
    currentRank: 5,
    targetRank: 3,
    opportunity: "+2.3K/週",
  },
  {
    keyword: "キャリア面談 無料",
    volume: "3.1K",
    currentRank: 12,
    targetRank: 6,
    opportunity: "+1.1K/週",
  },
  {
    keyword: "営業職 転職 事例",
    volume: "2.0K",
    currentRank: 18,
    targetRank: 8,
    opportunity: "+760/週",
  },
];

const backlinkFocus = [
  {
    domain: "marketing-hub.jp",
    rating: 67,
    anchor: "転職成功事例レポート",
    action: "返答済み",
  },
  {
    domain: "hr-expert.io",
    rating: 59,
    anchor: "人材採用テンプレ",
    action: "要リマインド",
  },
  {
    domain: "growthweekly.com",
    rating: 72,
    anchor: "BtoBマーケ年間計画",
    action: "初回送付済み",
  },
];

const alertFeed = [
  {
    source: "GA4",
    title: "CVR が 14% 低下 (LP-SEO-042)",
    detail: "Heroコピーの AB テスト切替と同時期。CV 数 62 → 53",
    severity: "high",
  },
  {
    source: "GSC",
    title: "クリック急増: " + "転職 キャリア相談",
    detail: "掲載順位 15 → 9。構造化 FAQ を追加検討",
    severity: "medium",
  },
  {
    source: "社内CRM",
    title: "SQL化率 33%→24%",
    detail: "製造業セグメントでリード質低下。ナーチャリング要確認",
    severity: "medium",
  },
];

const pipelineSnapshot = [
  { stage: "MQL", count: 1210, trend: 10.2 },
  { stage: "SAL", count: 612, trend: 7.4 },
  { stage: "SQL", count: 284, trend: -3.1 },
  { stage: "受注", count: 74, trend: 4.0 },
];

function TrendPill({ change }: { change: number }) {
  const isPositive = change >= 0;
  const Icon = isPositive ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
        isPositive
          ? "bg-emerald-100 text-emerald-700"
          : "bg-rose-100 text-rose-700"
      }`}
    >
      <Icon className="size-3" />
      {Math.abs(change).toFixed(1)}%
    </span>
  );
}

export default function MarketingDashboardPage() {
  const totalSessions = channelBreakdown.reduce(
    (sum, item) => sum + item.sessions,
    0
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">
              分析ダッシュボード
            </h1>
            <Badge variant="secondary" className="gap-1 text-sm">
              <LinkIcon className="size-3" /> 仮データ
            </Badge>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {kpis.map((item) => (
            <Card key={item.label}>
              <CardHeader className="pb-2">
                <CardDescription>{item.label}</CardDescription>
                <CardTitle className="text-3xl font-semibold">
                  {item.value}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 text-sm text-muted-foreground">
                <TrendPill change={item.change} />
                <span className="ml-2">vs 直近30日</span>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-6 grid gap-4 xl:grid-cols-12">
          <Card className="xl:col-span-7">
            <CardHeader className="pb-3">
              <CardTitle>チャネル別セッション (GA4)</CardTitle>
              <CardDescription>
                オーガニック + 有償リターゲティングのトラフィック推移
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {channelBreakdown.map((channel) => {
                const ratio = (channel.sessions / totalSessions) * 100;
                return (
                  <div key={channel.name}>
                    <div className="flex items-center justify-between text-sm">
                      <p className="font-medium">{channel.name}</p>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <TrendPill change={channel.trend} />
                        <span>{channel.sessions.toLocaleString()} セッション</span>
                      </div>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-muted">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-sky-500 to-indigo-500"
                        style={{ width: `${ratio}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Card className="xl:col-span-5">
            <CardHeader className="pb-3">
              <CardTitle>ファネル進捗 (社内CRM)</CardTitle>
              <CardDescription>週次 MQL→受注 推移</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {pipelineSnapshot.map((stage) => (
                <div
                  key={stage.stage}
                  className="flex items-center justify-between rounded-lg border px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium">{stage.stage}</p>
                    <p className="text-xs text-muted-foreground">今週</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-semibold">{stage.count}</p>
                    <TrendPill change={stage.trend} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="mt-6 grid gap-4 xl:grid-cols-12">
          <Card className="xl:col-span-7">
            <CardHeader className="pb-3">
              <CardTitle>キーワード優先度 (Ahrefs + GSC)</CardTitle>
              <CardDescription>インパクト×難易度で抽出した改善対象</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="pb-2 font-medium">クエリ</th>
                    <th className="pb-2 font-medium">月間Vol.</th>
                    <th className="pb-2 font-medium">現順位</th>
                    <th className="pb-2 font-medium">目標</th>
                    <th className="pb-2 font-medium">想定流入</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  {keywordInsights.map((row) => (
                    <tr key={row.keyword}>
                      <td className="py-3 font-medium">{row.keyword}</td>
                      <td className="py-3">{row.volume}</td>
                      <td className="py-3">#{row.currentRank}</td>
                      <td className="py-3">#{row.targetRank}</td>
                      <td className="py-3 text-emerald-600">{row.opportunity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <Card className="xl:col-span-5">
            <CardHeader className="pb-3">
              <CardTitle>被リンクリーチ (Ahrefs)</CardTitle>
              <CardDescription>Priority Outreach リスト</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {backlinkFocus.map((item) => (
                <div key={item.domain} className="rounded-xl border px-4 py-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold">{item.domain}</p>
                      <p className="text-xs text-muted-foreground">
                        DR {item.rating} ・ アンカー: {item.anchor}
                      </p>
                    </div>
                    <Badge
                      variant={item.action === "要リマインド" ? "destructive" : "secondary"}
                      className="text-xs"
                    >
                      {item.action}
                    </Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="mt-6 grid gap-4 xl:grid-cols-12">
          <Card className="xl:col-span-7">
            <CardHeader className="pb-3">
              <CardTitle>アクションフィード</CardTitle>
              <CardDescription>異常検知 + 担当者へのフォロー事項</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {alertFeed.map((alert) => (
                <div key={alert.title} className="rounded-xl border p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
                        {alert.source}
                      </div>
                      <p className="mt-1 text-base font-semibold">{alert.title}</p>
                      <p className="text-sm text-muted-foreground">{alert.detail}</p>
                    </div>
                    <div
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                        alert.severity === "high"
                          ? "bg-rose-100 text-rose-700"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      <AlertTriangle className="size-3" />
                      {alert.severity.toUpperCase()}
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="xl:col-span-5">
            <CardHeader className="pb-3">
              <CardTitle>次アクション</CardTitle>
              <CardDescription>担当者アサイン済みのタスク</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {["LP-SEO-042 のコピー改善を 11/20 まで", "ナーチャリングメール #3 を GA4 イベント連携", "hr-expert.io へリマインド連絡"].map(
                (task) => (
                  <div key={task} className="flex items-start gap-3">
                    <span className="mt-1 inline-flex size-2 rounded-full bg-primary" />
                    <div>
                      <p className="text-sm font-medium">{task}</p>
                      <p className="text-xs text-muted-foreground">
                        Owner: Marketing Ops
                      </p>
                    </div>
                  </div>
                )
              )}
              <Separator />
              <button className="inline-flex items-center gap-2 text-sm font-medium text-primary">
                <ExternalLink className="size-4" />
                Notion プレイブックを開く
              </button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
