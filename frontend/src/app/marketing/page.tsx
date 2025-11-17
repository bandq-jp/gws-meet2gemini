"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { ChatKit, useChatKit } from "@openai/chatkit-react";
import { Badge } from "@/components/ui/badge";

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
        headers.set("x-marketing-client-secret", secret);
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
        className="flex-1 min-h-0 w-full overflow-hidden border border-border bg-background"
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
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        <Badge className="mb-2" variant="secondary">
          BETA
        </Badge>
        <h1 className="text-3xl font-bold">マーケティング AI コックピット</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          SEOや集客の問いを入力すると、内部ワークフローがAhrefs/GSC/GA4/検索ツールを自動で連携させます。
        </p>
      </div>
      <div className="flex-1 min-h-0">
        <MarketingChatCanvas promptPresets={marketingPrompts} />
      </div>
    </div>
  );
}
