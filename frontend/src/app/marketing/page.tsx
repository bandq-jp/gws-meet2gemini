"use client";

import Script from "next/script";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { DetailedHTMLProps, HTMLAttributes } from "react";
import { useRouter } from "next/navigation";
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
import {
  FileText,
  Code2,
  Sparkles,
  RefreshCw,
  PlusCircle,
  Copy,
  Download,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { ModelAssetSelector } from "@/components/marketing/ModelAssetSelector";
import { ModelAssetTable } from "@/components/marketing/ModelAssetTable";
import { ModelAssetForm } from "@/components/marketing/ModelAssetForm";

type Attachment = {
  file_id: string;
  filename?: string | null;
  container_id?: string | null;
  download_url: string;
  message_id?: string;
  created_at?: string | null;
};

const CHATKIT_URL = "/api/marketing/chatkit/server";
const CHATKIT_DOMAIN_KEY =
  process.env.NEXT_PUBLIC_MARKETING_CHATKIT_DOMAIN_KEY ?? "bnq-marketing";
// Pattern to match OpenAI file IDs (file-xxx, cfile-xxx) and sandbox URLs
const FILE_ID_PATTERN = /(file|cfile)-[A-Za-z0-9_-]+/;
const SANDBOX_URL_PATTERN = /sandbox:\/[^\s\)\]"'<>]+/;

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
  a: ({ children, href, ...props }) => {
    let finalHref = href ?? "";
    let isDownloadable = false;

    if (!href) {
      return (
        <a {...props}>
          {children}
        </a>
      );
    }

    const sandboxMatch = SANDBOX_URL_PATTERN.test(href);
    if (sandboxMatch) {
      console.warn(`Unconverted sandbox URL detected: ${href}`);
    }

    const fileIdMatch = href.match(FILE_ID_PATTERN);
    if (fileIdMatch) {
      isDownloadable = true;
      // Keep backend URLs (with query params) intact to preserve container_id
      const alreadyBackend = href.startsWith("/api/marketing/files/");
      if (!alreadyBackend) {
        finalHref = `/api/marketing/files/${fileIdMatch[0]}`;
      }
    }

    return (
      <a
        href={finalHref}
        className="text-blue-600 hover:text-blue-800 underline decoration-blue-300 hover:decoration-blue-500 transition-colors"
        target="_blank"
        rel="noopener noreferrer"
        download={isDownloadable ? true : undefined}
        {...props}
      >
        {children}
        {isDownloadable && <Download className="inline-block w-3 h-3 ml-1" />}
      </a>
    );
  },
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
  img: ({ src, alt, ...props }) => {
    let finalSrc = src ?? "";

    if (!src) {
      return <img alt={alt} {...props} />;
    }

    if (SANDBOX_URL_PATTERN.test(src)) {
      console.warn(`Unconverted sandbox URL in image src: ${src}`);
    }

    const fileIdMatch = src.match(FILE_ID_PATTERN);
    if (fileIdMatch) {
      const alreadyBackend = src.startsWith("/api/marketing/files/");
      if (!alreadyBackend) {
        finalSrc = `/api/marketing/files/${fileIdMatch[0]}`;
      }
    }

    return (
      <img
        src={finalSrc}
        alt={alt}
        className="rounded-lg shadow-md my-4 max-w-full h-auto"
        {...props}
      />
    );
  },
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

export type ModelAsset = {
  id: string;
  name: string;
  description?: string;
  reasoning_effort?: "low" | "medium" | "high";
  verbosity?: "low" | "medium" | "high";
  enable_web_search?: boolean;
  enable_code_interpreter?: boolean;
  enable_ga4?: boolean;
  enable_gsc?: boolean;
  enable_ahrefs?: boolean;
  enable_wordpress?: boolean;
  enable_canvas?: boolean;
  system_prompt_addition?: string | null;
  visibility?: "public" | "private";
  created_by?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
};

function SeoCanvas({ state, isResponding, onApply }: {
  state: CanvasState;
  isResponding: boolean;
  onApply: (body: string) => void;
}) {
  const handleCopyHtml = useCallback(async () => {
    if (!state.body) return;
    try {
      await navigator.clipboard.writeText(state.body);
      // TODO: Show toast notification
      alert("HTMLをクリップボードにコピーしました");
    } catch (err) {
      console.error("Failed to copy:", err);
      alert("コピーに失敗しました");
    }
  }, [state.body]);

  const handleDownloadHtml = useCallback(() => {
    if (!state.body) return;
    const blob = new Blob([state.body], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const filename = state.articleId
      ? `${state.articleId}.html`
      : `article-${new Date().toISOString().slice(0, 10)}.html`;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [state.body, state.articleId]);

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
                HTMLプレビュー
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
            <div className="flex-shrink-0 flex items-center justify-end gap-2 p-4 border-b bg-muted/20">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyHtml}
                disabled={!state.body}
              >
                <Copy className="h-3 w-3 mr-2" />
                HTMLをコピー
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadHtml}
                disabled={!state.body}
              >
                <Download className="h-3 w-3 mr-2" />
                HTMLをダウンロード
              </Button>
            </div>
            <div className="flex-1 min-h-0 p-4 overflow-auto bg-white">
              {state.body ? (
                <pre className="w-full p-4 bg-slate-900 text-slate-50 rounded-lg overflow-auto font-mono text-sm leading-relaxed whitespace-pre-wrap break-words">
                  <code>{state.body}</code>
                </pre>
              ) : (
                <div className="flex items-center justify-center h-full">
                  <p className="text-slate-400 text-base">
                    HTMLがまだ生成されていません
                  </p>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export type MarketingPageProps = {
  initialThreadId?: string | null;
};

function loadStoredCanvas(threadId: string | null | undefined): CanvasState | null {
  if (typeof window === "undefined" || !threadId) return null;
  try {
    const raw = localStorage.getItem(`seo-canvas:${threadId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      return { visible: true, ...parsed };
    }
  } catch {
    // ignore malformed storage
  }
  return null;
}

function persistCanvas(threadId: string | null, state: CanvasState) {
  if (typeof window === "undefined" || !threadId) return;
  try {
    localStorage.setItem(
      `seo-canvas:${threadId}`,
      JSON.stringify({ ...state, visible: true })
    );
  } catch {
    // storage quota/full – best-effort
  }
}

export default function MarketingPage({ initialThreadId = null }: MarketingPageProps) {
  const router = useRouter();
  const tokenRef = useRef<TokenState>({ secret: null, expiresAt: 0 });
  const chatkitRef = useRef<ChatKitElement | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [assets, setAssets] = useState<ModelAsset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("marketing:model_asset_id") || "standard";
    }
    return "standard";
  });
  const [showAssetDialog, setShowAssetDialog] = useState(false);
  const [showManageDialog, setShowManageDialog] = useState(false);
  const [savingAsset, setSavingAsset] = useState(false);
  const [canvas, setCanvas] = useState<CanvasState>(() => {
    const stored = loadStoredCanvas(initialThreadId);
    return stored ?? { visible: false, version: 0 };
  });
  const [isResponding, setIsResponding] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const currentThreadIdRef = useRef<string | null>(initialThreadId ?? null);
  const currentAssetIdRef = useRef<string>(selectedAssetId);
  const canvasEnabled = useMemo(() => {
    const asset = assets.find((a) => a.id === selectedAssetId);
    if (!asset) return true;
    return asset.enable_canvas ?? true;
  }, [assets, selectedAssetId]);

  const marketingPrompts = useMemo(
    () => [
      "hitocareer.com の自然検索トラフィックが落ち込んでいる理由を洗い出して改善案を提案して",
      "SEO観点で『転職 コンサルタント』の競合比較と勝ち筋をまとめて",
      "GA4で直帰率が跳ねたページを見つけて、改善するための仮説を提示して",
      "Ahrefsの被リンクデータとGSCクエリを突き合わせてリライト優先度を教えて",
      "WordPress上の過去記事を踏まえて『エンジニア 転職 失敗』に関する新規記事のアウトラインと本文を書いて",
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

    // Persist for download proxy so <a> links can forward credentials
    try {
      const maxAge = Math.max((data.expires_in ?? 900) - 5, 60); // guard against very small TTLs
      const secure = typeof window !== "undefined" && window.location.protocol === "https:";
      document.cookie = `marketing_client_secret=${data.client_secret}; Path=/; Max-Age=${maxAge}; SameSite=Lax${secure ? "; Secure" : ""}`;
    } catch (err) {
      console.warn("Failed to set marketing_client_secret cookie", err);
    }

    return tokenRef.current.secret!;
  }, []);

  const customFetch = useCallback(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      try {
        const secret = await ensureClientSecret();
        const original = new Request(input, init);
        const headers = new Headers(original.headers);
        headers.set("x-marketing-client-secret", secret);
        headers.set("x-model-asset-id", currentAssetIdRef.current);
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

  const loadAttachments = useCallback(
    async (threadId: string | null) => {
      if (!threadId) {
        setAttachments([]);
        return;
      }
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(`/api/marketing/threads/${threadId}/attachments`, {
          headers: { "x-marketing-client-secret": secret },
          cache: "no-store",
        });
        if (!res.ok) throw new Error(`failed to fetch attachments: ${res.status}`);
        const data = await res.json();
        setAttachments(data.attachments || []);
      } catch (err) {
        console.error("loadAttachments failed", err);
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
        uploadStrategy: {
          type: "two_phase",
        },
      },
      locale: "ja",
      theme: "light",
      header: {
        enabled: true,
           title: { enabled: true, text: "マーケティング分析アシスタント" },
      },
      history: { enabled: true, showDelete: false, showRename: true },
      initialThread: initialThreadId ?? null,
      startScreen: {
        greeting: "SEOや集客課題を入力すると分析フローが自動で走ります。記事生成指示で右ペインが開きます。",
        prompts: marketingPrompts.map((p) => ({ label: p, prompt: p })),
      },
      composer: {
        placeholder: "例: WordPressの過去記事を参考に『エンジニア 転職 失敗』記事を書いて",
        attachments: {
          enabled: true,
          maxSize: 20 * 1024 * 1024,
          maxCount: 5,
          accept: {
            "text/csv": [".csv"],
            "application/pdf": [".pdf"],
            "text/plain": [".txt", ".md"],
            "application/vnd.ms-excel": [".xls", ".xlsx"],
          },
        },
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
        if (!canvasEnabled) {
          return { ok: false, disabled: true };
        }
        if (name === "seo_open_canvas") {
          setCanvas((prev) => {
            const next: CanvasState = {
              ...prev,
              visible: true,
              articleId:
                typeof params.articleId === "string"
                  ? params.articleId
                  : prev.articleId,
              topic:
                typeof params.topic === "string" ? params.topic : prev.topic,
              primaryKeyword:
                typeof params.primaryKeyword === "string"
                  ? params.primaryKeyword
                  : prev.primaryKeyword,
              outline:
                typeof params.outline === "string"
                  ? params.outline
                  : prev.outline,
            };
            persistCanvas(currentThreadIdRef.current, next);
            return next;
          });
          return { opened: true };
        }
        if (name === "seo_update_canvas") {
          setCanvas((prev) => {
            const next: CanvasState = {
              ...prev,
              visible: true,
              articleId:
                typeof params.articleId === "string"
                  ? params.articleId
                  : prev.articleId,
              title:
                typeof params.title === "string" ? params.title : prev.title,
              outline:
                typeof params.outline === "string"
                  ? params.outline
                  : prev.outline,
              body: typeof params.body === "string" ? params.body : prev.body,
              version:
                typeof params.version === "number"
                  ? params.version
                  : (prev.version ?? 0) + 1,
              status:
                typeof params.status === "string" ? params.status : prev.status,
            };
            persistCanvas(currentThreadIdRef.current, next);
            return next;
          });
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
  }, [customFetch, marketingPrompts, initialThreadId, canvasEnabled]);

  // Listen for response start/end to toggle spinner (from ChatKit custom events)
  useEffect(() => {
    const el = chatkitRef.current;
    if (!el) return;
    const onStart = () => setIsResponding(true);
    const onEnd = () => {
      setIsResponding(false);
      loadAttachments(currentThreadIdRef.current);
    };
    const handleThread = (threadId: string | null) => {
      currentThreadIdRef.current = threadId;
      const stored = loadStoredCanvas(threadId);
      setCanvas(stored ?? { visible: false, version: 0 });
      // Update URL without remounting the page (avoid interrupting in-flight sends)
      const target = threadId ? `/marketing/${threadId}` : "/marketing";
      if (typeof window !== "undefined" && window.location.pathname !== target) {
        window.history.replaceState({}, "", target);
      }
      loadAttachments(threadId);
    };
    const onThreadChange = (event: Event) => {
      const detail = (event as CustomEvent<{ threadId: string | null }>).detail;
      handleThread(detail?.threadId ?? null);
    };
    const onThreadLoadEnd = (event: Event) => {
      const detail = (event as CustomEvent<{ threadId: string }>)?.detail;
      handleThread(detail?.threadId ?? null);
    };

    el.addEventListener("chatkit.response.start", onStart);
    el.addEventListener("chatkit.response.end", onEnd);
    el.addEventListener("chatkit.thread.change", onThreadChange);
    el.addEventListener("chatkit.thread.load.end", onThreadLoadEnd);
    return () => {
      el.removeEventListener("chatkit.response.start", onStart);
      el.removeEventListener("chatkit.response.end", onEnd);
      el.removeEventListener("chatkit.thread.change", onThreadChange);
      el.removeEventListener("chatkit.thread.load.end", onThreadLoadEnd);
    };
  }, [router]);

  const handleApplyLocal = useCallback(
    (body: string) => {
      if (!canvasEnabled) return;
      const text = `Canvasで直接編集しました。最新本文を適用してください。articleId: ${canvas.articleId ?? "(not set)"}\n\n=== 新しい本文 ===\n${body}`;
      const el = chatkitRef.current as ChatKitElement | null;
      type SenderCapable = { sendUserMessage?: (msg: { content: string }) => void };
      const sender = el && (el as unknown as SenderCapable).sendUserMessage;
      if (sender) {
        sender({ content: text });
      }
    },
    [canvas.articleId, canvasEnabled]
  );

  const handleSelectAsset = useCallback((id: string) => {
    setSelectedAssetId(id);
    currentAssetIdRef.current = id;
    if (typeof window !== "undefined") {
      localStorage.setItem("marketing:model_asset_id", id);
    }
  }, []);

  // Load model assets once token is available
  useEffect(() => {
    const loadAssets = async () => {
      try {
        const secret = await ensureClientSecret();
        const res = await fetch("/api/marketing/model-assets", {
          headers: { "x-marketing-client-secret": secret },
          cache: "no-store",
        });
        if (!res.ok) throw new Error("モデルアセット取得に失敗しました");
        const data = await res.json();
        const list: ModelAsset[] = (data?.data ?? []).map((a: ModelAsset) => ({
          ...a,
          enable_canvas: a.enable_canvas ?? true,
        }));
        const withDefault =
          list.length && list.find((a) => a.id === "standard")
            ? list
            : [
                {
                  id: "standard",
                  name: "スタンダード",
                  visibility: "public",
                  enable_canvas: true,
                } as ModelAsset,
                ...list,
              ];
        setAssets(withDefault);
        if (withDefault.length && !withDefault.find((a) => a.id === currentAssetIdRef.current)) {
          handleSelectAsset(withDefault[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadAssets();
  }, [ensureClientSecret, handleSelectAsset]);

  useEffect(() => {
    loadAttachments(initialThreadId ?? null);
  }, [initialThreadId, loadAttachments]);

  const handleSaveAsset = useCallback(
    async (form: Partial<ModelAsset>, assetId?: string) => {
      setSavingAsset(true);
      try {
        const secret = await ensureClientSecret();
        const url = assetId
          ? `/api/marketing/model-assets/${assetId}`
          : "/api/marketing/model-assets";
        const method = assetId ? "PUT" : "POST";

        const res = await fetch(url, {
          method,
          headers: {
            "Content-Type": "application/json",
            "x-marketing-client-secret": secret,
          },
          body: JSON.stringify(form),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail?.error || "モデルアセットの保存に失敗しました");
        }
        const data = await res.json();
        const saved: ModelAsset = {
          ...(data?.data || {}),
          enable_canvas: (data?.data || {}).enable_canvas ?? true,
        };
        setAssets((prev) => {
          const filtered = prev.filter((a) => a.id !== saved.id);
          return [saved, ...filtered];
        });
        if (!assetId) {
          handleSelectAsset(saved.id);
        }
        setShowAssetDialog(false);
      } catch (err) {
        console.error(err);
        alert(err instanceof Error ? err.message : "モデルアセットの保存に失敗しました");
      } finally {
        setSavingAsset(false);
      }
    },
    [ensureClientSecret, handleSelectAsset]
  );

  const handleDeleteAsset = useCallback(
    async (assetId: string) => {
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(`/api/marketing/model-assets/${assetId}`, {
          method: "DELETE",
          headers: {
            "x-marketing-client-secret": secret,
          },
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail?.error || "モデルアセットの削除に失敗しました");
        }
        setAssets((prev) => prev.filter((a) => a.id !== assetId));
        if (selectedAssetId === assetId) {
          const standardAsset = assets.find((a) => a.id === "standard");
          if (standardAsset) {
            handleSelectAsset(standardAsset.id);
          }
        }
      } catch (err) {
        console.error(err);
        throw err;
      }
    },
    [ensureClientSecret, selectedAssetId, assets, handleSelectAsset]
  );

  useEffect(() => {
    if (!canvasEnabled && canvas.visible) {
      setCanvas((prev) => ({ ...prev, visible: false }));
    }
  }, [canvasEnabled, canvas.visible]);

  const showCanvasPane = canvasEnabled && canvas.visible;

  return (
    <>
      <Script
        src="https://cdn.platform.openai.com/deployments/chatkit/chatkit.js"
        strategy="beforeInteractive"
        crossOrigin="anonymous"
      />
      {/* Make CI download links look like buttons even inside ChatKit messages */}
      <style jsx global>{`
        openai-chatkit a[href^="/api/marketing/files/"] {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 10px;
          border-radius: 8px;
          border: 1px solid #2563eb;
          background: #eef2ff;
          color: #1d4ed8 !important;
          font-weight: 600;
          text-decoration: none !important;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
          transition: transform 120ms ease, box-shadow 120ms ease, background 120ms ease;
        }
        openai-chatkit a[href^="/api/marketing/files/"]:hover {
          background: #dbeafe;
          box-shadow: 0 4px 12px rgba(37, 99, 235, 0.18);
          transform: translateY(-1px);
        }
        openai-chatkit a[href^="/api/marketing/files/"]::before {
          content: "⬇";
          font-size: 14px;
        }
      `}</style>
      <div className="h-full w-full overflow-hidden bg-background relative">
        {/* モデルアセットセレクター */}
        <div className="absolute top-4 left-4 z-40 flex items-center gap-3">
          <ModelAssetSelector
            assets={assets}
            selectedId={selectedAssetId}
            onSelect={handleSelectAsset}
            onManageClick={() => setShowManageDialog(true)}
            onCreateClick={() => setShowAssetDialog(true)}
          />
        </div>

        {/* 管理画面Dialog */}
        <Dialog open={showManageDialog} onOpenChange={setShowManageDialog}>
          <DialogContent className="max-w-6xl max-h-[90vh] p-6">
            <DialogHeader className="mb-4">
              <DialogTitle className="text-2xl font-bold">モデルアセット管理</DialogTitle>
              <p className="text-sm text-muted-foreground mt-2">
                カスタムプリセットの作成・編集・削除
              </p>
            </DialogHeader>
            <ModelAssetTable
              assets={assets}
              onSave={handleSaveAsset}
              onDelete={handleDeleteAsset}
            />
          </DialogContent>
        </Dialog>

        {/* 新規作成ダイアログ */}
        <Dialog open={showAssetDialog} onOpenChange={setShowAssetDialog}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>モデルアセットを作成</DialogTitle>
            </DialogHeader>
            <ModelAssetForm onSubmit={handleSaveAsset} loading={savingAsset} submitLabel="作成" />
          </DialogContent>
        </Dialog>

        {tokenError && (
          <div className="absolute top-20 left-4 right-4 z-50 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive shadow-sm">
            ⚠️ {tokenError}
          </div>
        )}
        <div className={`h-full flex ${tokenError ? 'pt-16' : ''}`}>
          <div
            className={`h-full overflow-hidden transition-all duration-300 ${
              showCanvasPane ? "w-[45%]" : "w-full"
            }`}
          >
            <openai-chatkit
              ref={(el) => {
                chatkitRef.current = el as ChatKitElement | null;
              }}
              style={{ width: "100%", height: "100%", display: "block" }}
            />
            {/* Attachment buttons rendered outside ChatKit */}
            {attachments.length > 0 && (
              <div className="absolute bottom-4 left-4 right-4 z-30">
                <div className="flex flex-wrap gap-2 bg-white/90 backdrop-blur border border-slate-200 shadow-lg rounded-lg p-3">
                  {attachments.map((att) => (
                    <a
                      key={`${att.message_id}-${att.file_id}`}
                      href={att.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-md border border-blue-200 text-blue-700 bg-blue-50 hover:bg-blue-100 transition"
                      download
                    >
                      <Download className="h-4 w-4" />
                      {att.filename || att.file_id}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
          {showCanvasPane && (
            <div className="h-full w-[55%] overflow-hidden border-l-2 animate-in slide-in-from-right duration-300">
              <SeoCanvas state={canvas} isResponding={isResponding} onApply={handleApplyLocal} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}
