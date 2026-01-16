"use client";

import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { ChatKit } from "@openai/chatkit-react";
import {
  useMarketingChatKit,
  type ModelAsset,
  type ShareInfo,
} from "@/hooks/use-marketing-chatkit";
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
  Copy,
  Download,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
    const hrefStr = typeof href === "string" ? href : "";
    let finalHref = hrefStr;
    let isDownloadable = false;

    if (!hrefStr) {
      return (
        <a {...props}>
          {children}
        </a>
      );
    }

    const sandboxMatch = SANDBOX_URL_PATTERN.test(hrefStr);
    if (sandboxMatch) {
      console.warn(`Unconverted sandbox URL detected: ${hrefStr}`);
    }

    const fileIdMatch = hrefStr.match(FILE_ID_PATTERN);
    if (fileIdMatch) {
      isDownloadable = true;
      // Keep backend URLs (with query params) intact to preserve container_id
      const alreadyBackend = hrefStr.startsWith("/api/marketing/files/");
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
    const srcStr = typeof src === "string" ? src : "";
    let finalSrc = srcStr;

    if (!srcStr) {
      return <img alt={alt} {...props} />;
    }

    if (SANDBOX_URL_PATTERN.test(srcStr)) {
      console.warn(`Unconverted sandbox URL in image src: ${srcStr}`);
    }

    const fileIdMatch = srcStr.match(FILE_ID_PATTERN);
    if (fileIdMatch) {
      const alreadyBackend = srcStr.startsWith("/api/marketing/files/");
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

// ModelAsset type is imported from use-marketing-chatkit hook
export type { ModelAsset } from "@/hooks/use-marketing-chatkit";

const SeoCanvas = memo(function SeoCanvas({ state, isResponding, onApply }: {
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
});

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
  const [assets, setAssets] = useState<ModelAsset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string>("standard");
  const [showAssetDialog, setShowAssetDialog] = useState(false);
  const [showManageDialog, setShowManageDialog] = useState(false);
  const [savingAsset, setSavingAsset] = useState(false);
  const [canvas, setCanvas] = useState<CanvasState>(() => {
    const stored = loadStoredCanvas(initialThreadId);
    return stored ?? { visible: false, version: 0 };
  });
  const [isResponding, setIsResponding] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [showAttachments, setShowAttachments] = useState(false);
  const [shareInfo, setShareInfo] = useState<ShareInfo | null>(null);
  const [isReadOnly, setIsReadOnly] = useState(false);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(initialThreadId ?? null);
  const currentThreadIdRef = useRef<string | null>(initialThreadId ?? null);

  // Load selectedAssetId from localStorage on mount (rerender-defer-reads pattern)
  useEffect(() => {
    const stored = localStorage.getItem("marketing:model_asset_id");
    if (stored) setSelectedAssetId(stored);
  }, []);

  const canvasEnabled = useMemo(() => {
    const asset = assets.find((a) => a.id === selectedAssetId);
    if (!asset) return true;
    return asset.enable_canvas ?? true;
  }, [assets, selectedAssetId]);

  const marketingPrompts = useMemo(
    () => [
      { label: "hitocareer.com の自然検索トラフィックが落ち込んでいる理由を洗い出して改善案を提案して", prompt: "hitocareer.com の自然検索トラフィックが落ち込んでいる理由を洗い出して改善案を提案して", icon: "analytics" as const },
      { label: "SEO観点で『転職 コンサルタント』の競合比較と勝ち筋をまとめて", prompt: "SEO観点で『転職 コンサルタント』の競合比較と勝ち筋をまとめて", icon: "search" as const },
      { label: "GA4で直帰率が跳ねたページを見つけて、改善するための仮説を提示して", prompt: "GA4で直帰率が跳ねたページを見つけて、改善するための仮説を提示して", icon: "chart" as const },
      { label: "Ahrefsの被リンクデータとGSCクエリを突き合わせてリライト優先度を教えて", prompt: "Ahrefsの被リンクデータとGSCクエリを突き合わせてリライト優先度を教えて", icon: "document" as const },
      { label: "WordPress上の過去記事を踏まえて『エンジニア 転職 失敗』に関する新規記事のアウトラインと本文を書いて", prompt: "WordPress上の過去記事を踏まえて『エンジニア 転職 失敗』に関する新規記事のアウトラインと本文を書いて", icon: "write" as const },
    ],
    []
  );

  // Canvas event handlers for the hook
  const handleCanvasOpen = useCallback((params: Record<string, unknown>) => {
    setCanvas((prev) => {
      const next: CanvasState = {
        ...prev,
        visible: true,
        articleId: typeof params.articleId === "string" ? params.articleId : prev.articleId,
        topic: typeof params.topic === "string" ? params.topic : prev.topic,
        primaryKeyword: typeof params.primaryKeyword === "string" ? params.primaryKeyword : prev.primaryKeyword,
        outline: typeof params.outline === "string" ? params.outline : prev.outline,
      };
      persistCanvas(currentThreadIdRef.current, next);
      return next;
    });
  }, []);

  const handleCanvasUpdate = useCallback((params: Record<string, unknown>) => {
    setCanvas((prev) => {
      const next: CanvasState = {
        ...prev,
        visible: true,
        articleId: typeof params.articleId === "string" ? params.articleId : prev.articleId,
        title: typeof params.title === "string" ? params.title : prev.title,
        outline: typeof params.outline === "string" ? params.outline : prev.outline,
        body: typeof params.body === "string" ? params.body : prev.body,
        version: typeof params.version === "number" ? params.version : (prev.version ?? 0) + 1,
        status: typeof params.status === "string" ? params.status : prev.status,
      };
      persistCanvas(currentThreadIdRef.current, next);
      return next;
    });
  }, []);

  // Thread change handler
  const handleThread = useCallback((threadId: string | null) => {
    currentThreadIdRef.current = threadId;
    setCurrentThreadId(threadId);
    const stored = loadStoredCanvas(threadId);
    setCanvas(stored ?? { visible: false, version: 0 });
    // Update URL without remounting the page (avoid interrupting in-flight sends)
    const target = threadId ? `/marketing/${threadId}` : "/marketing";
    if (typeof window !== "undefined" && window.location.pathname !== target) {
      window.history.replaceState({}, "", target);
    }
  }, []);

  // Asset selection handler (must be defined before hook)
  const handleSelectAsset = useCallback((id: string) => {
    setSelectedAssetId(id);
    if (typeof window !== "undefined") {
      localStorage.setItem("marketing:model_asset_id", id);
    }
  }, []);

  // Stable callback refs for hook (to avoid circular dependency)
  const shareToggleRef = useRef<(isShared: boolean) => void>(() => {});

  // Use the custom ChatKit hook
  const {
    control,
    sendUserMessage,
    tokenError,
    ensureClientSecret,
  } = useMarketingChatKit({
    initialThreadId,
    assets,
    selectedAssetId,
    onAssetSelect: handleSelectAsset,
    canvasEnabled,
    onCanvasOpen: handleCanvasOpen,
    onCanvasUpdate: handleCanvasUpdate,
    onThreadChange: (threadId) => {
      handleThread(threadId);
      loadAttachments(threadId);
      loadShareStatus(threadId);
    },
    onResponseStart: () => setIsResponding(true),
    onResponseEnd: () => {
      setIsResponding(false);
      loadAttachments(currentThreadIdRef.current);
    },
    marketingPrompts,
    // Share functionality
    currentThreadId,
    shareInfo,
    isResponding,
    onShareToggle: (isShared) => shareToggleRef.current(isShared),
    // Header actions
    onSettingsClick: () => setShowManageDialog(true),
  });

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

  const loadShareStatus = useCallback(
    async (threadId: string | null) => {
      if (!threadId) {
        setShareInfo(null);
        setIsReadOnly(false);
        return;
      }
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(`/api/marketing/threads/${threadId}/share`, {
          headers: { "x-marketing-client-secret": secret },
          cache: "no-store",
        });
        if (!res.ok) {
          // 404 means no access or thread not found
          if (res.status === 404) {
            setShareInfo(null);
            setIsReadOnly(false);
            return;
          }
          throw new Error(`failed to fetch share status: ${res.status}`);
        }
        const data: ShareInfo = await res.json();
        setShareInfo(data);
        // If not owner but can view (shared), set read-only mode
        setIsReadOnly(!data.is_owner && data.is_shared);
      } catch (err) {
        console.error("loadShareStatus failed", err);
        setShareInfo(null);
        setIsReadOnly(false);
      }
    },
    [ensureClientSecret]
  );

  const handleToggleShare = useCallback(
    async (isShared: boolean) => {
      const threadId = currentThreadIdRef.current;
      if (!threadId) return;
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(`/api/marketing/threads/${threadId}/share`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-marketing-client-secret": secret,
          },
          body: JSON.stringify({ is_shared: isShared }),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail?.detail || "共有設定の更新に失敗しました");
        }
        // Refresh share status after toggle
        await loadShareStatus(threadId);
      } catch (err) {
        console.error("handleToggleShare failed", err);
        alert(err instanceof Error ? err.message : "共有設定の更新に失敗しました");
      }
    },
    [ensureClientSecret, loadShareStatus]
  );

  // Update shareToggleRef to point to actual handler (fixes circular dependency)
  useEffect(() => {
    shareToggleRef.current = handleToggleShare;
  }, [handleToggleShare]);

  const handleApplyLocal = useCallback(
    (body: string) => {
      if (!canvasEnabled) return;
      const text = `Canvasで直接編集しました。最新本文を適用してください。articleId: ${canvas.articleId ?? "(not set)"}\n\n=== 新しい本文 ===\n${body}`;
      sendUserMessage({ text });
    },
    [canvas.articleId, canvasEnabled, sendUserMessage]
  );

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
          enable_meta_ads: a.enable_meta_ads ?? true,
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
                  enable_meta_ads: true,
                } as ModelAsset,
                ...list,
              ];
        setAssets(withDefault);
        if (withDefault.length && !withDefault.find((a) => a.id === selectedAssetId)) {
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
    loadShareStatus(initialThreadId ?? null);
  }, [initialThreadId, loadAttachments, loadShareStatus]);

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
          enable_meta_ads: (data?.data || {}).enable_meta_ads ?? true,
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
        {/* 閲覧専用バッジ（共有されたスレッドを閲覧中の場合） */}
        {isReadOnly && (
          <div className="absolute top-4 right-4 z-40">
            <Badge variant="secondary" className="bg-amber-100 text-amber-800 border-amber-200">
              閲覧専用
            </Badge>
          </div>
        )}

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
            className={`relative h-full overflow-hidden transition-all duration-300 ${
              showCanvasPane ? "w-[45%]" : "w-full"
            }`}
          >
            <ChatKit
              control={control}
              style={{ width: "100%", height: "100%", display: "block" }}
            />
            {/* Read-only overlay for shared viewers */}
            {isReadOnly && (
              <div className="absolute bottom-0 left-0 right-0 h-32 z-20 pointer-events-auto bg-gradient-to-t from-white via-white/95 to-transparent flex items-end justify-center pb-4">
                <div className="text-center px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg shadow-sm">
                  <p className="text-sm text-amber-800">
                    この会話は共有されています。閲覧のみ可能です。
                  </p>
                </div>
              </div>
            )}

            {/* Attachment panel toggle & list (floats above ChatKit but avoids composer) */}
            {attachments.length > 0 && (
              <>
                <div className="absolute bottom-4 right-4 z-30">
                  <button
                    type="button"
                    onClick={() => setShowAttachments((v) => !v)}
                    className="inline-flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
                  >
                    <Download className="h-4 w-4" />
                    添付 {attachments.length} 件
                  </button>
                </div>
                <div
                  className={`absolute bottom-16 right-4 z-30 w-80 max-w-[92vw] transition-all duration-200 ${
                    showAttachments ? "opacity-100 translate-y-0" : "opacity-0 pointer-events-none translate-y-2"
                  }`}
                >
                  <div className="bg-white/95 backdrop-blur rounded-xl shadow-2xl border border-slate-200 max-h-[55vh] overflow-y-auto">
                    <div className="px-4 py-3 border-b flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur rounded-t-xl">
                      <div className="text-sm font-semibold text-slate-800">添付ファイル</div>
                      <button
                        type="button"
                        className="text-xs text-slate-500 hover:text-slate-800"
                        onClick={() => setShowAttachments(false)}
                      >
                        閉じる
                      </button>
                    </div>
                    <ul className="divide-y divide-slate-100">
                      {attachments.map((att) => (
                        <li key={`${att.message_id}-${att.file_id}`}>
                          <a
                            href={att.download_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-start gap-3 px-4 py-3 hover:bg-blue-50 transition"
                            download
                          >
                            <div className="mt-0.5">
                              <Download className="h-4 w-4 text-blue-600" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-semibold text-slate-900 truncate">
                                {att.filename || att.file_id}
                              </div>
                              {att.created_at && (
                                <div className="text-xs text-slate-500">
                                  {new Date(att.created_at).toLocaleString("ja-JP", {
                                    timeZone: "Asia/Tokyo",
                                    year: "numeric",
                                    month: "2-digit",
                                    day: "2-digit",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </div>
                              )}
                            </div>
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </>
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
