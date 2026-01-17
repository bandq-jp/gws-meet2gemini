"use client";

import { useCallback, useRef, useState, useEffect, useMemo } from "react";
import { useChatKit, type UseChatKitOptions } from "@openai/chatkit-react";
import type {
  ModelOption,
  HeaderIcon,
  ChatKitIcon,
  ToolOption,
  ThemeOption,
} from "@openai/chatkit";

const CHATKIT_URL = "/api/marketing/chatkit/server";
const CHATKIT_DOMAIN_KEY =
  process.env.NEXT_PUBLIC_MARKETING_CHATKIT_DOMAIN_KEY ?? "bnq-marketing";

type TokenState = {
  secret: string | null;
  expiresAt: number;
};

type MarketingPrompt = {
  label: string;
  prompt: string;
  icon?: ChatKitIcon;
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
  enable_meta_ads?: boolean;
  enable_gsc?: boolean;
  enable_ahrefs?: boolean;
  enable_wordpress?: boolean;
  enable_canvas?: boolean;
  enable_zoho_crm?: boolean;
  system_prompt_addition?: string | null;
  visibility?: "public" | "private";
  created_by?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
};

export type ShareInfo = {
  thread_id: string;
  is_shared: boolean;
  share_url: string | null;
  owner_email: string;
  is_owner: boolean;
};

export type UseMarketingChatKitOptions = {
  initialThreadId?: string | null;
  assets: ModelAsset[];
  selectedAssetId: string;
  onAssetSelect: (assetId: string) => void;
  canvasEnabled: boolean;
  onCanvasOpen: (params: Record<string, unknown>) => void;
  onCanvasUpdate: (params: Record<string, unknown>) => void;
  onThreadChange: (threadId: string | null) => void;
  onResponseStart: () => void;
  onResponseEnd: () => void;
  marketingPrompts: MarketingPrompt[];
  // Share functionality
  currentThreadId: string | null;
  shareInfo: ShareInfo | null;
  isResponding: boolean;
  onShareClick: () => void;
  // Header actions
  onSettingsClick: () => void;
  // Theme customization
  themeOptions?: {
    radius?: "pill" | "round" | "soft" | "sharp";
    density?: "compact" | "normal" | "spacious";
  };
  // Tool menu configuration
  toolOptions?: ToolOption[];
  // Thread item actions
  enableFeedback?: boolean;
  enableRetry?: boolean;
};

// Helper to count enabled tools for an asset
function countEnabledTools(asset: ModelAsset): number {
  let count = 0;
  if (asset.enable_web_search) count++;
  if (asset.enable_code_interpreter) count++;
  if (asset.enable_ga4) count++;
  if (asset.enable_meta_ads) count++;
  if (asset.enable_gsc) count++;
  if (asset.enable_ahrefs) count++;
  if (asset.enable_wordpress) count++;
  if (asset.enable_canvas) count++;
  if (asset.enable_zoho_crm) count++;
  return count;
}

// Default tool options for the composer tool menu
const DEFAULT_TOOL_OPTIONS: ToolOption[] = [
  {
    id: "analysis",
    label: "深掘り分析",
    icon: "analytics",
    shortLabel: "分析",
    placeholderOverride: "詳細な分析を依頼してください...",
  },
  {
    id: "article",
    label: "記事作成",
    icon: "write",
    shortLabel: "記事",
    placeholderOverride: "記事のトピックやキーワードを入力...",
  },
  {
    id: "search",
    label: "Web検索",
    icon: "globe",
    shortLabel: "検索",
    placeholderOverride: "最新の情報を検索して回答します...",
  },
];

export function useMarketingChatKit(options: UseMarketingChatKitOptions) {
  const tokenRef = useRef<TokenState>({ secret: null, expiresAt: 0 });
  const [tokenError, setTokenError] = useState<string | null>(null);
  const currentAssetIdRef = useRef(options.selectedAssetId);

  // Update ref when selectedAssetId changes
  useEffect(() => {
    currentAssetIdRef.current = options.selectedAssetId;
  }, [options.selectedAssetId]);

  // Convert assets to ModelOption[] for ChatKit's composer.models
  const modelOptions: ModelOption[] = useMemo(() => {
    return options.assets.map((asset) => ({
      id: asset.id,
      label: asset.name,
      description: `${countEnabledTools(asset)}ツール${asset.description ? ` · ${asset.description}` : ""}`,
      default: asset.id === options.selectedAssetId,
    }));
  }, [options.assets, options.selectedAssetId]);

  // Store refs for header action callbacks
  const onSettingsClickRef = useRef(options.onSettingsClick);
  const onShareClickRef = useRef(options.onShareClick);
  const shareInfoRef = useRef(options.shareInfo);
  const currentThreadIdRef = useRef(options.currentThreadId);
  const isRespondingRef = useRef(options.isResponding);
  const onAssetSelectRef = useRef(options.onAssetSelect);

  useEffect(() => {
    onSettingsClickRef.current = options.onSettingsClick;
    onShareClickRef.current = options.onShareClick;
    shareInfoRef.current = options.shareInfo;
    currentThreadIdRef.current = options.currentThreadId;
    isRespondingRef.current = options.isResponding;
    onAssetSelectRef.current = options.onAssetSelect;
  }, [
    options.onSettingsClick,
    options.onShareClick,
    options.shareInfo,
    options.currentThreadId,
    options.isResponding,
    options.onAssetSelect,
  ]);

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
      const maxAge = Math.max((data.expires_in ?? 900) - 5, 60);
      const secure =
        typeof window !== "undefined" && window.location.protocol === "https:";
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
        const message =
          error instanceof Error ? error.message : "Token refresh failed";
        setTokenError(message);
        throw error;
      }
    },
    [ensureClientSecret]
  );

  // Store callbacks in refs to avoid recreation
  const onCanvasOpenRef = useRef(options.onCanvasOpen);
  const onCanvasUpdateRef = useRef(options.onCanvasUpdate);
  const onThreadChangeRef = useRef(options.onThreadChange);
  const onResponseStartRef = useRef(options.onResponseStart);
  const onResponseEndRef = useRef(options.onResponseEnd);
  const canvasEnabledRef = useRef(options.canvasEnabled);

  useEffect(() => {
    onCanvasOpenRef.current = options.onCanvasOpen;
    onCanvasUpdateRef.current = options.onCanvasUpdate;
    onThreadChangeRef.current = options.onThreadChange;
    onResponseStartRef.current = options.onResponseStart;
    onResponseEndRef.current = options.onResponseEnd;
    canvasEnabledRef.current = options.canvasEnabled;
  }, [
    options.onCanvasOpen,
    options.onCanvasUpdate,
    options.onThreadChange,
    options.onResponseStart,
    options.onResponseEnd,
    options.canvasEnabled,
  ]);

  // Determine share button icon based on share state
  // Using "book-open" as ChatKit doesn't have a share icon
  const getShareIcon = (): HeaderIcon => {
    if (!currentThreadIdRef.current) return "book-open";
    if (shareInfoRef.current?.is_shared) return "compose"; // "compose" suggests active/shared
    return "book-open";
  };

  // Handle share button click - opens dialog
  const handleShareClick = useCallback(() => {
    if (!currentThreadIdRef.current) return;
    onShareClickRef.current();
  }, []);

  // Handle settings button click
  const handleSettingsClick = useCallback(() => {
    onSettingsClickRef.current();
  }, []);

  // Build theme configuration
  const themeConfig: ThemeOption = {
    colorScheme: "light",
    radius: options.themeOptions?.radius ?? "round",
    density: options.themeOptions?.density ?? "normal",
    typography: {
      baseSize: 15,
    },
    color: {
      grayscale: {
        hue: 220,
        tint: 2,
      },
      accent: {
        primary: "hsl(220.9, 39.3%, 11%)",
        level: 1,
      },
    },
  };

  const chatkitOptions: UseChatKitOptions = {
    api: {
      url: CHATKIT_URL,
      domainKey: CHATKIT_DOMAIN_KEY,
      fetch: customFetch,
      uploadStrategy: {
        type: "two_phase",
      },
    },
    locale: "ja",
    theme: themeConfig,
    frameTitle: "マーケティング分析アシスタント",
    header: {
      enabled: true,
      title: { enabled: true, text: "マーケティング分析アシスタント" },
      leftAction: {
        icon: "settings-cog" as HeaderIcon,
        onClick: handleSettingsClick,
      },
      rightAction: options.currentThreadId
        ? {
            icon: getShareIcon(),
            onClick: handleShareClick,
          }
        : undefined,
    },
    history: { enabled: true, showDelete: false, showRename: true },
    initialThread: options.initialThreadId ?? null,
    // Thread item actions - feedback and retry buttons
    threadItemActions: {
      feedback: options.enableFeedback ?? true,
      retry: options.enableRetry ?? true,
    },
    startScreen: {
      greeting:
        "SEOや集客課題を入力すると分析フローが自動で走ります。記事生成指示で右ペインが開きます。",
      prompts: options.marketingPrompts.map((p) => ({
        label: p.label,
        prompt: p.prompt,
        icon: p.icon,
      })),
    },
    composer: {
      placeholder:
        "例: WordPressの過去記事を参考に『エンジニア 転職 失敗』記事を書いて",
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
      // Model selector inside ChatKit's composer
      models: modelOptions.length > 0 ? modelOptions : undefined,
      // Tool menu in composer (use default tools if none provided)
      tools: options.toolOptions ?? DEFAULT_TOOL_OPTIONS,
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
      if (!canvasEnabledRef.current) {
        return { ok: false, disabled: true };
      }
      if (name === "seo_open_canvas") {
        onCanvasOpenRef.current(params);
        return { opened: true };
      }
      if (name === "seo_update_canvas") {
        onCanvasUpdateRef.current(params);
        return { ok: true };
      }
      return { ok: true };
    },
    // Event handlers (chatkit-react format)
    onResponseStart: () => {
      onResponseStartRef.current();
    },
    onResponseEnd: () => {
      onResponseEndRef.current();
    },
    onThreadChange: (event: { threadId: string | null }) => {
      onThreadChangeRef.current(event.threadId);
    },
    onThreadLoadEnd: (event: { threadId: string }) => {
      onThreadChangeRef.current(event.threadId);
    },
  };

  const chatkit = useChatKit(chatkitOptions);

  return {
    ...chatkit,
    tokenError,
    ensureClientSecret,
  };
}
