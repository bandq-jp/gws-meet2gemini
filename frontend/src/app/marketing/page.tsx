"use client";

import Script from "next/script";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import type { Components } from "react-markdown";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, Code2, Sparkles, RefreshCw } from "lucide-react";

const CHATKIT_URL = "/api/marketing/chatkit/server";
const CHATKIT_DOMAIN_KEY =
  process.env.NEXT_PUBLIC_MARKETING_CHATKIT_DOMAIN_KEY ?? "bnq-marketing";

// Custom components for rich markdown/HTML rendering
const markdownComponents: Components = {
  h1: ({ children, ...props }) => (
    <h1 className="text-4xl font-bold mb-6 mt-8 pb-3 border-b-2 border-slate-200" {...props}>
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 className="text-3xl font-bold mb-4 mt-7 pb-2 border-b border-slate-200" {...props}>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 className="text-2xl font-bold mb-3 mt-6" {...props}>
      {children}
    </h3>
  ),
  h4: ({ children, ...props }) => (
    <h4 className="text-xl font-semibold mb-2 mt-5" {...props}>
      {children}
    </h4>
  ),
  h5: ({ children, ...props }) => (
    <h5 className="text-lg font-semibold mb-2 mt-4" {...props}>
      {children}
    </h5>
  ),
  h6: ({ children, ...props }) => (
    <h6 className="text-base font-semibold mb-2 mt-3" {...props}>
      {children}
    </h6>
  ),
  p: ({ children, ...props }) => (
    <p className="text-base leading-7 mb-4 text-slate-700" {...props}>
      {children}
    </p>
  ),
  a: ({ children, href, ...props }) => (
    <a
      href={href}
      className="text-blue-600 hover:text-blue-800 underline decoration-blue-300 hover:decoration-blue-500 transition-colors"
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    >
      {children}
    </a>
  ),
  strong: ({ children, ...props }) => (
    <strong className="font-bold text-slate-900" {...props}>
      {children}
    </strong>
  ),
  em: ({ children, ...props }) => (
    <em className="italic text-slate-700" {...props}>
      {children}
    </em>
  ),
  ul: ({ children, ...props }) => (
    <ul className="list-disc list-outside ml-6 mb-4 space-y-2" {...props}>
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol className="list-decimal list-outside ml-6 mb-4 space-y-2" {...props}>
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => (
    <li className="text-base leading-7 text-slate-700 pl-1" {...props}>
      {children}
    </li>
  ),
  blockquote: ({ children, ...props }) => (
    <blockquote
      className="border-l-4 border-blue-500 pl-4 py-2 my-4 italic bg-slate-50 text-slate-600"
      {...props}
    >
      {children}
    </blockquote>
  ),
  code: ({ children, className, ...props }) => {
    const isInline = !className;
    return isInline ? (
      <code
        className="bg-slate-100 text-pink-600 px-1.5 py-0.5 rounded text-sm font-mono"
        {...props}
      >
        {children}
      </code>
    ) : (
      <code className={`${className} text-sm`} {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children, ...props }) => (
    <pre
      className="bg-slate-900 text-slate-50 p-4 rounded-lg overflow-x-auto mb-4 text-sm leading-relaxed"
      {...props}
    >
      {children}
    </pre>
  ),
  hr: (props) => <hr className="my-8 border-t-2 border-slate-200" {...props} />,
  table: ({ children, ...props }) => (
    <div className="overflow-x-auto mb-4">
      <table className="min-w-full divide-y divide-slate-300 border border-slate-300" {...props}>
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead className="bg-slate-100" {...props}>
      {children}
    </thead>
  ),
  tbody: ({ children, ...props }) => (
    <tbody className="divide-y divide-slate-200 bg-white" {...props}>
      {children}
    </tbody>
  ),
  tr: ({ children, ...props }) => (
    <tr {...props}>
      {children}
    </tr>
  ),
  th: ({ children, ...props }) => (
    <th
      className="px-4 py-3 text-left text-sm font-semibold text-slate-900"
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ children, ...props }) => (
    <td className="px-4 py-3 text-sm text-slate-700" {...props}>
      {children}
    </td>
  ),
  img: ({ src, alt, ...props }) => (
    <img
      src={src}
      alt={alt}
      className="rounded-lg shadow-md my-4 max-w-full h-auto"
      {...props}
    />
  ),
};

type TokenState = {
  secret: string | null;
  expiresAt: number;
};

type CanvasState = {
  visible: boolean;
  articleId?: string;
  title?: string;
  outline?: string;
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
  const [draft, setDraft] = useState(state.body ?? "");

  useEffect(() => {
    setDraft(state.body ?? "");
  }, [state.body]);

  if (!state.visible) {
    return (
      <div className="h-full flex items-center justify-center bg-muted/20">
        <div className="flex flex-col items-center gap-3">
          <Sparkles className="h-12 w-12 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">
            キャンバスはツール使用時に表示されます
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden bg-white">
      {/* Header Section */}
      <div className="flex-shrink-0 space-y-3 p-4 border-b">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              <code className="text-xs font-mono text-muted-foreground">
                {state.articleId ?? "記事ID未確定"}
              </code>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={state.status === "published" ? "default" : "secondary"} className="font-medium">
                {state.status ?? "draft"}
              </Badge>
              <Badge variant="outline" className="font-mono text-xs">
                v{state.version ?? 0}
              </Badge>
              {state.topic && (
                <Badge variant="outline" className="text-xs">
                  {state.topic}
                </Badge>
              )}
              {state.primaryKeyword && (
                <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                  🔍 {state.primaryKeyword}
                </Badge>
              )}
            </div>
          </div>
          {isResponding && (
            <div className="flex items-center gap-2 text-xs text-primary">
              <RefreshCw className="h-3 w-3 animate-spin" />
              <span className="font-medium">生成中</span>
            </div>
          )}
        </div>

        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="meta" className="border-none">
            <AccordionTrigger className="py-2 text-sm font-semibold hover:no-underline">
              📝 タイトル・構成
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 pt-2">
                <div>
                  <div className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    タイトル
                  </div>
                  <div className="rounded-lg border bg-muted/30 px-4 py-3 text-sm font-medium text-foreground">
                    {state.title || "（未設定）"}
                  </div>
                </div>
                <div>
                  <div className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    アウトライン
                  </div>
                  <div className="max-h-32 overflow-auto rounded-lg border bg-muted/20 px-4 py-3">
                    <pre className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">
                      {state.outline || "（未設定）"}
                    </pre>
                  </div>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>

      {/* Content Section */}
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <Tabs defaultValue="preview" className="flex-1 flex flex-col min-h-0">
          <div className="px-4 pt-4">
            <TabsList className="grid w-full max-w-md grid-cols-2">
              <TabsTrigger value="preview" className="gap-2">
                <FileText className="h-4 w-4" />
                プレビュー
              </TabsTrigger>
              <TabsTrigger value="html" className="gap-2">
                <Code2 className="h-4 w-4" />
                HTML編集
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="preview" className="flex-1 min-h-0 mt-0 overflow-hidden">
            <div className="h-full overflow-auto px-4 py-6 bg-white">
              <div className="max-w-4xl mx-auto">
                <article className="article-preview">
                  {state.body ? (
                    <ReactMarkdown
                      components={markdownComponents}
                      remarkPlugins={[remarkGfm, remarkBreaks]}
                      rehypePlugins={[rehypeRaw, rehypeSanitize]}
                    >
                      {state.body}
                    </ReactMarkdown>
                  ) : (
                    <div className="text-center py-12">
                      <p className="text-slate-400 text-base">
                        本文がまだ生成されていません
                      </p>
                    </div>
                  )}
                </article>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="html" className="flex-1 min-h-0 mt-0 overflow-hidden flex flex-col">
            <div className="flex-1 min-h-0 p-4 overflow-auto">
              <textarea
                className="w-full h-full min-h-[500px] p-4 font-mono text-sm leading-relaxed resize-none border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="HTML または Markdown を入力..."
              />
            </div>
            <div className="flex-shrink-0 flex items-center justify-end gap-2 p-4 border-t bg-muted/20">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDraft(state.body ?? "")}
                disabled={draft === state.body}
              >
                <RefreshCw className="h-3 w-3 mr-2" />
                リセット
              </Button>
              <Button
                size="sm"
                onClick={() => onApply(draft)}
                disabled={draft === state.body || !draft.trim()}
              >
                この本文で更新してと伝える
              </Button>
            </div>
          </TabsContent>
        </Tabs>
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
            outline: params.outline ?? prev.outline,
          }));
          return { opened: true };
        }
        if (name === "seo_update_canvas") {
          setCanvas((prev) => ({
            ...prev,
            visible: true,
            articleId: params.articleId ?? prev.articleId,
            title: params.title ?? prev.title,
            outline: params.outline ?? prev.outline,
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
      <div className="h-full w-full overflow-hidden bg-background relative">
        {tokenError && (
          <div className="absolute top-2 left-2 right-2 z-50 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive shadow-sm">
            ⚠️ {tokenError}
          </div>
        )}
        <div className={`h-full flex ${tokenError ? 'pt-16' : ''}`}>
          <div
            className={`h-full overflow-hidden transition-all duration-300 ${
              canvas.visible ? "w-[45%]" : "w-full"
            }`}
          >
            <openai-chatkit
              ref={(el) => {
                chatkitRef.current = el as ChatKitElement | null;
              }}
              style={{ width: "100%", height: "100%", display: "block" }}
            />
          </div>
          {canvas.visible && (
            <div className="h-full w-[55%] overflow-hidden border-l-2 animate-in slide-in-from-right duration-300">
              <SeoCanvas state={canvas} isResponding={isResponding} onApply={handleApplyLocal} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}
