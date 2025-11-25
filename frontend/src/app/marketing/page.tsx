"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChatKit, useChatKit } from "@openai/chatkit-react";
import {
  Code2,
  Eye,
  Loader2,
  Save,
  SplitSquareVertical,
} from "lucide-react";
import Script from "next/script";

const CHATKIT_URL = "/api/marketing/chatkit/server";
const CHATKIT_DOMAIN_KEY =
  process.env.NEXT_PUBLIC_MARKETING_CHATKIT_DOMAIN_KEY ?? "bnq-marketing";

type TokenState = {
  secret: string | null;
  expiresAt: number;
};

type CanvasState = {
  visible: boolean;
  articleId?: string;
  title?: string;
  body?: string;
  version?: number;
  status?: string;
  topic?: string;
  primaryKeyword?: string;
};

type MarketingChatCanvasProps = {
  promptPresets: string[];
};

function SeoCanvasPanel({
  state,
  isResponding,
  onApplyLocal,
}: {
  state: CanvasState;
  isResponding: boolean;
  onApplyLocal: (body: string) => void;
}) {
  const [draftBody, setDraftBody] = useState(state.body ?? "");
  const [tab, setTab] = useState<"preview" | "html">("preview");

  useEffect(() => {
    setDraftBody(state.body ?? "");
  }, [state.body]);

  const rendered = state.body ?? "";

  return (
    <div className="flex w-full flex-col overflow-hidden rounded-lg border bg-white shadow-sm">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <SplitSquareVertical className="h-4 w-4" />
            <span>SEO Canvas</span>
          </div>
          <div className="font-mono text-xs text-muted-foreground">
            {state.articleId ?? "(articleId 未確定)"}
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="rounded-full bg-emerald-50 px-2 py-1 text-emerald-700">
            {state.status ?? "draft"}
          </span>
          <span>v{state.version ?? 0}</span>
          {isResponding && <Loader2 className="h-4 w-4 animate-spin" />}
        </div>
      </div>

      <div className="flex items-center gap-3 border-b px-4 py-2 text-xs font-medium">
        <button
          className={`inline-flex items-center gap-1 rounded-md px-2 py-1 ${
            tab === "preview" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
          }`}
          onClick={() => setTab("preview")}
        >
          <Eye className="h-4 w-4" />
          プレビュー
        </button>
        <button
          className={`inline-flex items-center gap-1 rounded-md px-2 py-1 ${
            tab === "html" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
          }`}
          onClick={() => setTab("html")}
        >
          <Code2 className="h-4 w-4" />
          HTML
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {tab === "preview" ? (
          <div className="prose max-w-none prose-sm sm:prose-base">
            <div
              dangerouslySetInnerHTML={{ __html: rendered || "<p>まだ本文がありません。</p>" }}
            />
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <textarea
              className="min-h-[360px] w-full rounded-md border p-3 font-mono text-xs leading-relaxed"
              value={draftBody}
              onChange={(e) => setDraftBody(e.target.value)}
            />
            <div className="flex items-center justify-end gap-2">
              <button
                className="inline-flex items-center gap-1 rounded-md border px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted"
                onClick={() => setDraftBody(state.body ?? "")}
              >
                リセット
              </button>
              <button
                className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground shadow hover:opacity-90"
                onClick={() => onApplyLocal(draftBody)}
              >
                <Save className="h-4 w-4" />
                この本文で更新してと伝える
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MarketingChatCanvas({ promptPresets }: MarketingChatCanvasProps) {
  const tokenRef = useRef<TokenState>({ secret: null, expiresAt: 0 });
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [canvas, setCanvas] = useState<CanvasState>({ visible: false, version: 0 });

  const ensureClientSecret = useCallback(async () => {
    const now = Date.now();
    if (tokenRef.current.secret && tokenRef.current.expiresAt - 5_000 > now) {
      return tokenRef.current.secret;
    }
    const hasSecret = Boolean(tokenRef.current.secret);
    const endpoint = hasSecret
      ? "/api/marketing/chatkit/refresh"
      : "/api/marketing/chatkit/start";
    const response = await fetch(endpoint, {
      method: "POST",
      body: hasSecret
        ? JSON.stringify({ currentClientSecret: tokenRef.current.secret })
        : undefined,
      headers: hasSecret ? { "Content-Type": "application/json" } : undefined,
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
        const message = error instanceof Error ? error.message : "Token refresh failed";
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

  const onClientTool = useCallback(
    async (toolCall: { name: string; params?: Record<string, unknown> }) => {
      const { name, params = {} } = toolCall;

      if (name === "seo_open_canvas") {
        setCanvas((prev) => ({
          ...prev,
          visible: true,
          articleId: (params.articleId as string | undefined) ?? prev.articleId,
          topic: (params.topic as string | undefined) ?? prev.topic,
          primaryKeyword:
            (params.primaryKeyword as string | undefined) ?? prev.primaryKeyword,
        }));
        return { opened: true };
      }

      if (name === "seo_update_canvas") {
        setCanvas((prev) => ({
          ...prev,
          visible: true,
          articleId: (params.articleId as string | undefined) ?? prev.articleId,
          title: (params.title as string | undefined) ?? prev.title,
          body: (params.body as string | undefined) ?? prev.body,
          version: (params.version as number | undefined) ?? (prev.version ?? 0) + 1,
          status: (params.status as string | undefined) ?? prev.status,
        }));
        return { ok: true };
      }

      throw new Error(`Unknown client tool: ${name}`);
    },
    []
  );

  const {
    control,
    sendUserMessage,
    isResponding = false,
  } = useChatKit({
    api: {
      url: CHATKIT_URL,
      domainKey: CHATKIT_DOMAIN_KEY,
      fetch: customFetch,
    },
    onClientTool,
    theme: {
      colorScheme: "light",
      radius: "soft",
      density: "spacious",
    },
    header: {
      enabled: true,
      title: { enabled: true, text: "マーケティング分析アシスタント" },
    },
    history: { enabled: true, showDelete: false, showRename: true },
    startScreen: {
      greeting: "SEOや集客課題を入力すると分析フローが自動で走ります。記事生成指示で右ペインが開きます。",
      prompts: startScreenPrompts,
    },
    composer: {
      placeholder: "例: BtoB SaaS導入メリットについてSEO記事を書いて",
      attachments: { enabled: false },
    },
    disclaimer: {
      text: "生成されたインサイトは社内共有前に必ず確認してください。",
      highContrast: true,
    },
  });

  const handleApplyLocalEdit = useCallback(
    (body: string) => {
      if (!sendUserMessage) return;
      const text = `Canvasで直接修正しました。最新本文を適用してください。\narticleId: ${
        canvas.articleId ?? "(not set)"
      }\n\n=== 新しい本文 ===\n${body}`;
      sendUserMessage({ content: text });
    },
    [sendUserMessage, canvas.articleId]
  );

  return (
    <div className="flex h-full flex-col gap-3">
      {tokenError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {tokenError}
        </div>
      )}
      <div className="flex h-[calc(100vh-160px)] min-h-[640px] flex-col gap-3 lg:flex-row">
        <div className="min-h-[420px] flex-1 overflow-hidden rounded-lg border bg-background">
          <ChatKit control={control} className="h-full w-full" />
        </div>

        {canvas.visible && (
          <div className="min-h-[420px] flex-1">
            <SeoCanvasPanel
              state={canvas}
              isResponding={isResponding}
              onApplyLocal={handleApplyLocalEdit}
            />
          </div>
        )}
      </div>
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
      "BtoB SaaS 導入メリットに関するSEO記事を3000文字で下書きから書いて",
    ],
    []
  );

  return (
    <>
      <Script
        src="https://cdn.platform.openai.com/deployments/chatkit/chatkit.js"
        async
        crossOrigin="anonymous"
        strategy="afterInteractive"
      />
      <div className="flex h-full flex-col">
        <div className="flex-1 min-h-0">
          <MarketingChatCanvas promptPresets={marketingPrompts} />
        </div>
      </div>
    </>
  );
}
