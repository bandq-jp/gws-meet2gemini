"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { ChatKit, useChatKit } from "@openai/chatkit-react";
import {
  ArrowUpRight,
  BarChart3,
  Bolt,
  Globe,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const CHATKIT_URL = "/api/marketing/chatkit/server";
const CHATKIT_DOMAIN_KEY =
  process.env.NEXT_PUBLIC_MARKETING_CHATKIT_DOMAIN_KEY ?? "bnq-marketing";

type TokenState = {
  secret: string | null;
  expiresAt: number;
};

type MarketingChatCanvasProps = {
  promptPresets: string[];
};

function MarketingChatCanvas({ promptPresets }: MarketingChatCanvasProps) {
  const tokenRef = useRef<TokenState>({ secret: null, expiresAt: 0 });
  const [tokenError, setTokenError] = useState<string | null>(null);

  const ensureClientSecret = useCallback(async () => {
    const now = Date.now();
    if (
      tokenRef.current.secret &&
      tokenRef.current.expiresAt - 5_000 > now
    ) {
      return tokenRef.current.secret;
    }
    const hasSecret = Boolean(tokenRef.current.secret);
    const endpoint = hasSecret
      ? "/api/marketing/chatkit/refresh"
      : "/api/marketing/chatkit/start";
    const response = await fetch(endpoint, {
      method: "POST",
      body: hasSecret
        ? JSON.stringify({
            currentClientSecret: tokenRef.current.secret,
          })
        : undefined,
      headers: hasSecret
        ? {
            "Content-Type": "application/json",
          }
        : undefined,
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail?.error || "Failed to fetch client secret");
    }
    const data = await response.json();
    tokenRef.current = {
      secret: data.client_secret,
      expiresAt: now + (data.expires_in ?? 900) * 1000,
    };
    return tokenRef.current.secret!;
  }, []);

  const customFetch = useCallback(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      try {
        const secret = await ensureClientSecret();
        const originalRequest = new Request(input, init);
        const headers = new Headers(originalRequest.headers);
        headers.set("Authorization", `Bearer ${secret}`);
        setTokenError(null);
        return fetch(new Request(originalRequest, { headers }));
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Token refresh failed";
        setTokenError(message);
        throw error;
      }
    },
    [ensureClientSecret]
  );

  const startScreenPrompts = useMemo(
    () => promptPresets.map((prompt) => ({ label: prompt, prompt })),
    [promptPresets]
  );

  const { control } = useChatKit({
    api: {
      url: CHATKIT_URL,
      domainKey: CHATKIT_DOMAIN_KEY,
      fetch: customFetch,
    },
    theme: {
      colorScheme: "light",
      radius: "soft",
      density: "spacious",
    },
    header: {
      enabled: true,
      title: {
        enabled: true,
        text: "マーケティング分析アシスタント",
      },
    },
    history: {
      enabled: true,
      showDelete: false,
      showRename: true,
    },
    startScreen: {
      greeting: "SEOや集客課題を入力すると分析フローが自動で走ります。",
      prompts: startScreenPrompts,
    },
    composer: {
      placeholder:
        "例: 直近30日でCVが落ちたランディングページの原因を突き止めたい",
      attachments: {
        enabled: false,
      },
    },
    disclaimer: {
      text: "生成されたインサイトは社内共有前に必ず確認してください。",
      highContrast: true,
    },
  });

  return (
    <div className="flex h-full flex-col gap-3">
      {tokenError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {tokenError}
        </div>
      )}
      <ChatKit
        control={control}
        className="h-[calc(100vh-280px)] min-h-[480px] w-full overflow-hidden rounded-xl border border-border bg-background shadow-sm"
      />
    </div>
  );
}

export default function MarketingPage() {
  const marketingPrompts = useMemo(
    () => [
      "hitocareer.com の自然検索トラフィックが落ち込んでいる理由を洗い出して改善案を提案して",
      "SEO観点で『転職 コンサルタント』の競合比較と勝ち筋をまとめて",
      "GA4で直帰率が跳ねたページを見つけて、改善するための仮説を提示して",
      "Ahrefsの被リンクデータとGSCクエリを突き合わせてリライト優先度を教えて",
    ],
    []
  );
  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-6">
        <Badge className="mb-3" variant="secondary">
          BETA
        </Badge>
        <h1 className="text-3xl font-bold">マーケティング AI コックピット</h1>
        <p className="text-muted-foreground">
          Ahrefs / GSC / GA4 / Web検索をChatKitで束ね、ChatGPTライクな体験でSEO調査・施策立案を行えます。
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="lg:col-span-1">
          <CardHeader className="space-y-1">
            <CardTitle className="flex items-center justify-between text-lg">
              SEOリサーチチャット
              <Badge variant="outline" className="text-xs font-normal">
                Streaming / Progress updates
              </Badge>
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              左上の履歴から過去スレッドを選択、右下のコンポーザーに課題を入力してください。
              ProgressUpdateEventで推論ステップも逐次可視化されます。
            </p>
          </CardHeader>
          <CardContent>
            <MarketingChatCanvas promptPresets={marketingPrompts} />
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Bolt className="h-4 w-4 text-primary" />
                推論フロー概要
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div>
                <p className="font-medium">1. Ahrefs スキャン</p>
                <p className="text-muted-foreground">
                  DR/被リンク/キーワード順位を取得し、トレンド変化を可視化。
                </p>
              </div>
              <div>
                <p className="font-medium">2. 追加深掘りポイント抽出</p>
                <p className="text-muted-foreground">
                  変動が大きいクエリや競合比で弱い領域をリストアップ。
                </p>
              </div>
              <div>
                <p className="font-medium">3. GSC/GA4 クロス分析</p>
                <p className="text-muted-foreground">
                  CTR・離脱率・新規/リピーター比などを照合し、UX観点の示唆を追加。
                </p>
              </div>
              <div>
                <p className="font-medium">4. 施策整理</p>
                <p className="text-muted-foreground">
                  優先度付きTODO、改善仮説、検証ステップを提案します。
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldCheck className="h-4 w-4 text-primary" />
                セキュリティメモ
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-start gap-2">
                <Badge variant="outline">JWT</Badge>
                <p className="text-muted-foreground">
                  Next.js APIで短命なクライアントシークレットを発行し、FastAPI側でHMAC検証。
                </p>
              </div>
              <div className="flex items-start gap-2">
                <Badge variant="outline">Supabase</Badge>
                <p className="text-muted-foreground">
                  /marketing_conversations + /marketing_messagesにChatKitのThread/ItemをJSON保存。
                </p>
              </div>
              <div className="flex items-start gap-2">
                <Badge variant="outline">Streaming</Badge>
                <p className="text-muted-foreground">
                  SSEでProgressUpdateEventを受信し、UI側でローディング段階を可視化。
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Globe className="h-4 w-4 text-primary" />
                推奨入力例
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {marketingPrompts.slice(0, 3).map((prompt) => (
                <div
                  key={prompt}
                  className="rounded-md border border-dashed border-border/70 px-3 py-2"
                >
                  {prompt}
                </div>
              ))}
              <Separator />
              <Button
                variant="outline"
                className="w-full"
                onClick={() =>
                  window.open(
                    "https://openai.github.io/chatkit-python/",
                    "_blank"
                  )
                }
              >
                <BarChart3 className="mr-2 h-4 w-4" />
                ChatKit サーバー設計ガイド
                <ArrowUpRight className="ml-1 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
