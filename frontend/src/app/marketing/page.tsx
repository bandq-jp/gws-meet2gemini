"use client";

import Script from "next/script";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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

type ChatKitElement = HTMLElement & {
  setOptions: (opts: Record<string, unknown>) => void;
  addEventListener: typeof window.addEventListener;
};

function SeoCanvas({ state, isResponding, onApply }: {
  state: CanvasState;
  isResponding: boolean;
  onApply: (body: string) => void;
}) {
  const [tab, setTab] = useState<"preview" | "html">("preview");
  const [draft, setDraft] = useState(state.body ?? "");

  useEffect(() => {
    setDraft(state.body ?? "");
  }, [state.body]);

  if (!state.visible) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        キャンバスはまだ開かれていません
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border bg-white shadow-sm">
      <div className="flex items-center justify-between border-b px-4 py-3 text-xs text-muted-foreground">
        <div className="space-y-1">
          <div className="font-mono">
            {state.articleId ?? "(articleId 未確定)"}
          </div>
          <div className="flex gap-2">
            <span className="rounded bg-emerald-50 px-2 py-1 text-emerald-700">
              {state.status ?? "draft"}
            </span>
            <span>v{state.version ?? 0}</span>
          </div>
        </div>
        {isResponding && <span className="animate-pulse">生成中…</span>}
      </div>

      <div className="flex items-center gap-2 border-b px-4 py-2 text-xs">
        <button
          className={`rounded px-2 py-1 ${tab === "preview" ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
          onClick={() => setTab("preview")}
        >
          プレビュー
        </button>
        <button
          className={`rounded px-2 py-1 ${tab === "html" ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
          onClick={() => setTab("html")}
        >
          HTML
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {tab === "preview" ? (
          <div className="prose max-w-none prose-sm sm:prose-base">
            <div
              dangerouslySetInnerHTML={{
                __html: state.body || "<p>本文がまだありません。</p>",
              }}
            />
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <textarea
              className="min-h-[360px] w-full rounded-md border p-3 font-mono text-xs leading-relaxed"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            <div className="flex items-center justify-end gap-2">
              <button
                className="rounded border px-3 py-2 text-xs text-muted-foreground hover:bg-muted"
                onClick={() => setDraft(state.body ?? "")}
              >
                リセット
              </button>
              <button
                className="rounded bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground shadow hover:opacity-90"
                onClick={() => onApply(draft)}
              >
                この本文で更新してと伝える
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function MarketingPage() {
  const tokenRef = useRef<TokenState>({ secret: null, expiresAt: 0 });
  const chatkitRef = useRef<ChatKitElement | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [canvas, setCanvas] = useState<CanvasState>({ visible: false, version: 0 });
  const [isResponding, setIsResponding] = useState(false);

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
        const original = new Request(input, init);
        const headers = new Headers(original.headers);
        headers.set("x-marketing-client-secret", secret);
        setTokenError(null);
        return fetch(new Request(original, { headers }));
      } catch (error) {
        const message = error instanceof Error ? error.message : "Token refresh failed";
        setTokenError(message);
        throw error;
      }
    },
    [ensureClientSecret]
  );

  // Set options once ChatKit custom element is ready
  useEffect(() => {
    const el = chatkitRef.current;
    if (!el) return;

    const options = {
      api: {
        url: CHATKIT_URL,
        domainKey: CHATKIT_DOMAIN_KEY,
        fetch: customFetch,
      },
      locale: "ja",
      theme: "light",
      header: {
        enabled: true,
        title: { enabled: true, text: "マーケティング分析アシスタント" },
      },
      history: { enabled: true, showDelete: false, showRename: true },
      startScreen: {
        greeting: "SEOや集客課題を入力すると分析フローが自動で走ります。記事生成指示で右ペインが開きます。",
        prompts: marketingPrompts.map((p) => ({ label: p, prompt: p })),
      },
      composer: {
        placeholder: "例: BtoB SaaS導入メリットについてSEO記事を書いて",
        attachments: { enabled: false },
      },
      disclaimer: {
        text: "生成されたインサイトは社内共有前に必ず確認してください。",
        highContrast: true,
      },
      onClientTool: async ({
        name,
        params,
      }: {
        name: string;
        params: Record<string, unknown>;
      }) => {
        if (name === "seo_open_canvas") {
          setCanvas((prev) => ({
            ...prev,
            visible: true,
            articleId: params.articleId ?? prev.articleId,
            topic: params.topic ?? prev.topic,
            primaryKeyword: params.primaryKeyword ?? prev.primaryKeyword,
          }));
          return { opened: true };
        }
        if (name === "seo_update_canvas") {
          setCanvas((prev) => ({
            ...prev,
            visible: true,
            articleId: params.articleId ?? prev.articleId,
            title: params.title ?? prev.title,
            body: params.body ?? prev.body,
            version: params.version ?? (prev.version ?? 0) + 1,
            status: params.status ?? prev.status,
          }));
          return { ok: true };
        }
        return { ok: true };
      },
    };

    // Ensure custom element is defined then set options
    const setup = async () => {
      if (customElements.get("openai-chatkit")) {
        el.setOptions(options);
      } else {
        await customElements.whenDefined("openai-chatkit");
        el.setOptions(options);
      }
    };
    setup();
  }, [customFetch, marketingPrompts]);

  // Listen for response start/end to toggle spinner (from ChatKit custom events)
  useEffect(() => {
    const el = chatkitRef.current;
    if (!el) return;
    const onStart = () => setIsResponding(true);
    const onEnd = () => setIsResponding(false);
    el.addEventListener("chatkit.response.start", onStart);
    el.addEventListener("chatkit.response.end", onEnd);
    return () => {
      el.removeEventListener("chatkit.response.start", onStart);
      el.removeEventListener("chatkit.response.end", onEnd);
    };
  }, []);

  const handleApplyLocal = useCallback(
    (body: string) => {
      const text = `Canvasで直接編集しました。最新本文を適用してください。articleId: ${canvas.articleId ?? "(not set)"}\n\n=== 新しい本文 ===\n${body}`;
      const el = chatkitRef.current as ChatKitElement | null;
      type SenderCapable = { sendUserMessage?: (msg: { content: string }) => void };
      const sender = el && (el as unknown as SenderCapable).sendUserMessage;
      if (sender) {
        sender({ content: text });
      }
    },
    [canvas.articleId]
  );

  return (
    <>
      <Script
        src="https://cdn.platform.openai.com/deployments/chatkit/chatkit.js"
        strategy="beforeInteractive"
        crossOrigin="anonymous"
      />
      <div className="flex h-full flex-col gap-3">
        {tokenError && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
            {tokenError}
          </div>
        )}
        <div className="flex h-[calc(100vh-160px)] min-h-[640px] flex-col gap-3 lg:flex-row">
          <div className="min-h-[420px] flex-1 overflow-hidden rounded-lg border bg-background">
            <openai-chatkit
              ref={(el) => {
                chatkitRef.current = el as ChatKitElement | null;
              }}
              style={{ width: "100%", height: "100%", display: "block" }}
            />
          </div>
          <div className="min-h-[420px] flex-1">
            <SeoCanvas state={canvas} isResponding={isResponding} onApply={handleApplyLocal} />
          </div>
        </div>
      </div>
    </>
  );
}
