"use client";

import { useCallback, useRef, useState, useEffect } from "react";
import { useChatKit, type UseChatKitOptions } from "@openai/chatkit-react";

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
};

export type UseMarketingChatKitOptions = {
  initialThreadId?: string | null;
  selectedAssetId: string;
  canvasEnabled: boolean;
  onCanvasOpen: (params: Record<string, unknown>) => void;
  onCanvasUpdate: (params: Record<string, unknown>) => void;
  onThreadChange: (threadId: string | null) => void;
  onResponseStart: () => void;
  onResponseEnd: () => void;
  marketingPrompts: MarketingPrompt[];
};

export function useMarketingChatKit(options: UseMarketingChatKitOptions) {
  const tokenRef = useRef<TokenState>({ secret: null, expiresAt: 0 });
  const [tokenError, setTokenError] = useState<string | null>(null);
  const currentAssetIdRef = useRef(options.selectedAssetId);

  // Update ref when selectedAssetId changes
  useEffect(() => {
    currentAssetIdRef.current = options.selectedAssetId;
  }, [options.selectedAssetId]);

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
    theme: "light",
    header: {
      enabled: true,
      title: { enabled: true, text: "マーケティング分析アシスタント" },
    },
    history: { enabled: true, showDelete: false, showRename: true },
    initialThread: options.initialThreadId ?? null,
    startScreen: {
      greeting:
        "SEOや集客課題を入力すると分析フローが自動で走ります。記事生成指示で右ペインが開きます。",
      prompts: options.marketingPrompts.map((p) => ({
        label: p.label,
        prompt: p.prompt,
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
