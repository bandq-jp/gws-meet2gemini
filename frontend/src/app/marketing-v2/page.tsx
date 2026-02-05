"use client";

/**
 * Marketing AI Chat Page (V2 - Google ADK + Gemini)
 *
 * Clean, editorial-style chat interface.
 * Uses root-level AppSidebar from SidebarLayout.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  MarketingChat,
  type ModelAsset,
  type ShareInfo,
  type Attachment,
  type MarketingChatRef,
} from "@/components/marketing/v2/MarketingChat";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ModelAssetTable } from "@/components/marketing/ModelAssetTable";
import { ModelAssetForm } from "@/components/marketing/ModelAssetForm";
import { ShareDialog } from "@/components/marketing/share-dialog";
import { HistoryPanel, type Conversation } from "@/components/marketing/v2/HistoryPanel";

// Default asset
const DEFAULT_ASSET: ModelAsset = {
  id: "standard",
  name: "Standard",
  visibility: "public",
};

// Token management
type TokenState = {
  secret: string | null;
  expiresAt: number;
};

export type MarketingV2PageProps = {
  initialThreadId?: string | null;
};

export default function MarketingV2Page({
  initialThreadId = null,
}: MarketingV2PageProps) {
  // State
  const [assets, setAssets] = useState<ModelAsset[]>([DEFAULT_ASSET]);
  const [assetsLoaded, setAssetsLoaded] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState<string>("standard");
  const [showManageDialog, setShowManageDialog] = useState(false);
  const [showAssetDialog, setShowAssetDialog] = useState(false);
  const [savingAsset, setSavingAsset] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [shareInfo, setShareInfo] = useState<ShareInfo | null>(null);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);
  const [isReadOnly, setIsReadOnly] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(
    initialThreadId
  );

  // History Panel state
  const [historyOpen, setHistoryOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Token management
  const tokenRef = useRef<TokenState>({ secret: null, expiresAt: 0 });

  // Chat ref for triggering new conversation
  const chatRef = useRef<MarketingChatRef | null>(null);

  // Load selectedAssetId from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("marketing-v2:model_asset_id");
    if (stored) setSelectedAssetId(stored);
  }, []);

  // Ensure we have a valid token
  const ensureClientSecret = useCallback(async (): Promise<string> => {
    const now = Date.now();
    if (tokenRef.current.secret && tokenRef.current.expiresAt - 5_000 > now) {
      return tokenRef.current.secret;
    }

    const hasSecret = Boolean(tokenRef.current.secret);
    const endpoint = hasSecret
      ? "/api/marketing-v2/chatkit/refresh"
      : "/api/marketing-v2/chatkit/start";

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

    // Persist for download proxy
    try {
      const maxAge = Math.max((data.expires_in ?? 900) - 5, 60);
      const secure =
        typeof window !== "undefined" && window.location.protocol === "https:";
      document.cookie = `marketing_v2_client_secret=${data.client_secret}; Path=/; Max-Age=${maxAge}; SameSite=Lax${secure ? "; Secure" : ""}`;
    } catch (err) {
      console.warn("Failed to set cookie", err);
    }

    return tokenRef.current.secret!;
  }, []);

  // Asset selection handler
  const handleSelectAsset = useCallback((id: string) => {
    setSelectedAssetId(id);
    if (typeof window !== "undefined") {
      localStorage.setItem("marketing-v2:model_asset_id", id);
    }
  }, []);

  // New conversation handler
  const handleNewConversation = useCallback(() => {
    setCurrentConversationId(null);
    if (typeof window !== "undefined" && window.location.pathname !== "/marketing-v2") {
      window.history.replaceState({}, "", "/marketing-v2");
    }
    setAttachments([]);
    setShareInfo(null);
    setIsReadOnly(false);
    // Clear chat messages
    chatRef.current?.clearMessages();
  }, []);

  // Select conversation from history
  const handleSelectConversation = useCallback((conv: Conversation) => {
    setCurrentConversationId(conv.id);
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", `/marketing-v2/${conv.id}`);
    }
    // Load attachments and share status
    loadAttachments(conv.id);
    loadShareStatus(conv.id);
  }, []);

  // Conversation change handler (from chat component)
  const handleConversationChange = useCallback(
    (conversationId: string | null) => {
      setCurrentConversationId(conversationId);

      // Update URL without remounting
      const target = conversationId
        ? `/marketing-v2/${conversationId}`
        : "/marketing-v2";
      if (typeof window !== "undefined" && window.location.pathname !== target) {
        window.history.replaceState({}, "", target);
      }

      // Refresh history panel
      setRefreshTrigger((t) => t + 1);

      // Load attachments and share status
      loadAttachments(conversationId);
      loadShareStatus(conversationId);
    },
    []
  );

  // Load attachments
  const loadAttachments = useCallback(
    async (conversationId: string | null) => {
      if (!conversationId) {
        setAttachments([]);
        return;
      }
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(
          `/api/marketing-v2/threads/${conversationId}/attachments`,
          {
            headers: { "x-marketing-client-secret": secret },
            cache: "no-store",
          }
        );
        if (!res.ok) throw new Error(`Failed: ${res.status}`);
        const data = await res.json();
        setAttachments(data.attachments || []);
      } catch (err) {
        console.error("loadAttachments failed", err);
      }
    },
    [ensureClientSecret]
  );

  // Load share status
  const loadShareStatus = useCallback(
    async (conversationId: string | null) => {
      if (!conversationId) {
        setShareInfo(null);
        setIsReadOnly(false);
        return;
      }
      setShareLoading(true);
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(
          `/api/marketing-v2/threads/${conversationId}/share`,
          {
            headers: { "x-marketing-client-secret": secret },
            cache: "no-store",
          }
        );
        if (!res.ok) {
          if (res.status === 404) {
            setShareInfo(null);
            setIsReadOnly(false);
            return;
          }
          throw new Error(`Failed: ${res.status}`);
        }
        const data: ShareInfo = await res.json();
        setShareInfo(data);
        setIsReadOnly(!data.is_owner && data.is_shared);
      } catch (err) {
        console.error("loadShareStatus failed", err);
        setShareInfo(null);
        setIsReadOnly(false);
      } finally {
        setShareLoading(false);
      }
    },
    [ensureClientSecret]
  );

  // Toggle share
  const handleToggleShare = useCallback(
    async (isShared: boolean) => {
      if (!currentConversationId) return;
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(
          `/api/marketing-v2/threads/${currentConversationId}/share`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "x-marketing-client-secret": secret,
            },
            body: JSON.stringify({ is_shared: isShared }),
          }
        );
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail?.detail || "Failed to update share settings");
        }
        await loadShareStatus(currentConversationId);
      } catch (err) {
        console.error("handleToggleShare failed", err);
        alert(err instanceof Error ? err.message : "Failed to update share settings");
      }
    },
    [currentConversationId, ensureClientSecret, loadShareStatus]
  );

  // Load model assets
  useEffect(() => {
    const loadAssets = async () => {
      try {
        const secret = await ensureClientSecret();
        const res = await fetch("/api/marketing/model-assets", {
          headers: { "x-marketing-client-secret": secret },
          cache: "no-store",
        });
        if (!res.ok) throw new Error("Failed to load model assets");
        const data = await res.json();
        const list: ModelAsset[] = data?.data ?? [];
        const withDefault =
          list.length && list.find((a) => a.id === "standard")
            ? list
            : [DEFAULT_ASSET, ...list];
        setAssets(withDefault);
        setAssetsLoaded(true);
        if (
          withDefault.length &&
          !withDefault.find((a) => a.id === selectedAssetId)
        ) {
          handleSelectAsset(withDefault[0].id);
        }
      } catch (err) {
        console.error(err);
        setAssetsLoaded(true);
      }
    };
    loadAssets();
  }, [ensureClientSecret, handleSelectAsset, selectedAssetId]);

  // Initial load
  useEffect(() => {
    loadAttachments(initialThreadId);
    loadShareStatus(initialThreadId);
  }, [initialThreadId, loadAttachments, loadShareStatus]);

  // Save asset
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
          throw new Error(detail?.error || "Failed to save model asset");
        }
        const data = await res.json();
        const saved: ModelAsset = data?.data || {};
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
        alert(err instanceof Error ? err.message : "Failed to save");
      } finally {
        setSavingAsset(false);
      }
    },
    [ensureClientSecret, handleSelectAsset]
  );

  // Delete asset
  const handleDeleteAsset = useCallback(
    async (assetId: string) => {
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(`/api/marketing/model-assets/${assetId}`, {
          method: "DELETE",
          headers: { "x-marketing-client-secret": secret },
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail?.error || "Failed to delete");
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

  return (
    <>
      {/* Model Asset Management Dialog */}
      <Dialog open={showManageDialog} onOpenChange={setShowManageDialog}>
        <DialogContent className="max-w-6xl max-h-[90vh] p-6">
          <DialogHeader className="mb-4">
            <DialogTitle className="text-xl font-semibold">
              モデルアセット管理
            </DialogTitle>
            <p className="text-sm text-muted-foreground mt-1">
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

      {/* New Asset Dialog */}
      <Dialog open={showAssetDialog} onOpenChange={setShowAssetDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>新規モデルアセット</DialogTitle>
          </DialogHeader>
          <ModelAssetForm
            onSubmit={handleSaveAsset}
            loading={savingAsset}
            submitLabel="作成"
          />
        </DialogContent>
      </Dialog>

      {/* Share Dialog */}
      <ShareDialog
        open={showShareDialog}
        onOpenChange={setShowShareDialog}
        shareInfo={shareInfo}
        isLoading={shareLoading}
        onToggleShare={handleToggleShare}
      />

      {/* History Panel (right sheet) */}
      <HistoryPanel
        open={historyOpen}
        onOpenChange={setHistoryOpen}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        refreshTrigger={refreshTrigger}
        getClientSecret={ensureClientSecret}
      />

      {/* Main Chat - Full height, no extra sidebar/header */}
      <MarketingChat
        ref={chatRef}
        initialConversationId={initialThreadId}
        assets={assets}
        selectedAssetId={selectedAssetId}
        onAssetSelect={handleSelectAsset}
        onConversationChange={handleConversationChange}
        onSettingsClick={() => setShowManageDialog(true)}
        onShareClick={() => setShowShareDialog(true)}
        onHistoryClick={() => setHistoryOpen(true)}
        shareInfo={shareInfo}
        attachments={attachments}
        isReadOnly={isReadOnly}
        className="h-full"
      />
    </>
  );
}
