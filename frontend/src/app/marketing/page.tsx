"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useMarketingChat } from "@/hooks/use-marketing-chat";
import type { ModelAsset, ShareInfo } from "@/lib/marketing-types";
import { Badge } from "@/components/ui/badge";
import {
  Download,
  History,
  Settings,
  Share2,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ModelAssetTable } from "@/components/marketing/ModelAssetTable";
import { ModelAssetForm } from "@/components/marketing/ModelAssetForm";
import { ShareDialog } from "@/components/marketing/share-dialog";
import { ChatWindow } from "@/components/marketing/chat/ChatWindow";
import { HistoryPanel } from "@/components/marketing/chat/HistoryPanel";

type Attachment = {
  file_id: string;
  filename?: string | null;
  container_id?: string | null;
  download_url: string;
  message_id?: string;
  created_at?: string | null;
};

const DEFAULT_ASSET: ModelAsset = {
  id: "standard",
  name: "スタンダード",
  visibility: "public",
  enable_canvas: true,
  enable_meta_ads: true,
};

export type MarketingPageProps = {
  initialThreadId?: string | null;
};

export default function MarketingPage({
  initialThreadId = null,
}: MarketingPageProps) {
  // Model assets
  const [assets, setAssets] = useState<ModelAsset[]>([DEFAULT_ASSET]);
  const [selectedAssetId, setSelectedAssetId] = useState<string>("standard");
  const [showAssetDialog, setShowAssetDialog] = useState(false);
  const [showManageDialog, setShowManageDialog] = useState(false);
  const [savingAsset, setSavingAsset] = useState(false);

  // Attachments
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [showAttachments, setShowAttachments] = useState(false);

  // Share
  const [shareInfo, setShareInfo] = useState<ShareInfo | null>(null);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);
  const [isReadOnly, setIsReadOnly] = useState(false);

  // History
  const [showHistory, setShowHistory] = useState(false);

  const currentThreadIdRef = useRef<string | null>(initialThreadId ?? null);

  // Chat hook
  const {
    messages,
    sendMessage,
    isStreaming,
    stopStreaming,
    clearMessages,
    loadConversation,
    currentConversationId,
    setConversationId,
    pendingQuestionGroup,
    respondToQuestions,
    ensureClientSecret,
  } = useMarketingChat();

  // Load selectedAssetId from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("marketing:model_asset_id");
    if (stored) setSelectedAssetId(stored);
  }, []);

  const handleSelectAsset = useCallback((id: string) => {
    setSelectedAssetId(id);
    if (typeof window !== "undefined") {
      localStorage.setItem("marketing:model_asset_id", id);
    }
  }, []);

  // Sync currentThreadIdRef
  useEffect(() => {
    currentThreadIdRef.current = currentConversationId;
  }, [currentConversationId]);

  // Load initial thread
  useEffect(() => {
    if (initialThreadId) {
      loadConversation(initialThreadId);
    }
  }, [initialThreadId, loadConversation]);

  // --- Attachments ---

  const loadAttachments = useCallback(
    async (threadId: string | null) => {
      if (!threadId) {
        setAttachments([]);
        return;
      }
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(
          `/api/marketing/threads/${threadId}/attachments`,
          {
            headers: { "x-marketing-client-secret": secret },
            cache: "no-store",
          }
        );
        if (!res.ok) return;
        const data = await res.json();
        setAttachments(data.attachments || []);
      } catch (err) {
        console.error("loadAttachments failed", err);
      }
    },
    [ensureClientSecret]
  );

  // --- Share ---

  const loadShareStatus = useCallback(
    async (threadId: string | null) => {
      if (!threadId) {
        setShareInfo(null);
        setIsReadOnly(false);
        return;
      }
      setShareLoading(true);
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(
          `/api/marketing/threads/${threadId}/share`,
          {
            headers: { "x-marketing-client-secret": secret },
            cache: "no-store",
          }
        );
        if (!res.ok) {
          setShareInfo(null);
          setIsReadOnly(false);
          return;
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

  const handleToggleShare = useCallback(
    async (isShared: boolean) => {
      const threadId = currentThreadIdRef.current;
      if (!threadId) return;
      try {
        const secret = await ensureClientSecret();
        const res = await fetch(
          `/api/marketing/threads/${threadId}/share`,
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
          throw new Error(
            detail?.detail || "共有設定の更新に失敗しました"
          );
        }
        await loadShareStatus(threadId);
      } catch (err) {
        console.error("handleToggleShare failed", err);
        alert(
          err instanceof Error ? err.message : "共有設定の更新に失敗しました"
        );
      }
    },
    [ensureClientSecret, loadShareStatus]
  );

  // Load attachments/share on initial thread
  useEffect(() => {
    loadAttachments(initialThreadId ?? null);
    loadShareStatus(initialThreadId ?? null);
  }, [initialThreadId, loadAttachments, loadShareStatus]);

  // Reload on conversation change
  useEffect(() => {
    if (currentConversationId) {
      loadAttachments(currentConversationId);
      loadShareStatus(currentConversationId);
    }
  }, [currentConversationId, loadAttachments, loadShareStatus]);

  // --- Model assets ---

  useEffect(() => {
    const loadAssets = async () => {
      try {
        const secret = await ensureClientSecret();
        const res = await fetch("/api/marketing/model-assets", {
          headers: { "x-marketing-client-secret": secret },
          cache: "no-store",
        });
        if (!res.ok) return;
        const data = await res.json();
        const list: ModelAsset[] = (data?.data ?? []).map(
          (a: ModelAsset) => ({
            ...a,
            enable_canvas: a.enable_canvas ?? true,
            enable_meta_ads: a.enable_meta_ads ?? true,
          })
        );
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
        if (
          withDefault.length &&
          !withDefault.find((a) => a.id === selectedAssetId)
        ) {
          handleSelectAsset(withDefault[0].id);
        }
      } catch (err) {
        console.error("loadAssets failed", err);
      }
    };
    loadAssets();
  }, [ensureClientSecret, handleSelectAsset]);

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
          throw new Error(
            detail?.error || "モデルアセットの保存に失敗しました"
          );
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
        alert(
          err instanceof Error
            ? err.message
            : "モデルアセットの保存に失敗しました"
        );
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
          headers: { "x-marketing-client-secret": secret },
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(
            detail?.error || "モデルアセットの削除に失敗しました"
          );
        }
        setAssets((prev) => prev.filter((a) => a.id !== assetId));
        if (selectedAssetId === assetId) {
          handleSelectAsset("standard");
        }
      } catch (err) {
        console.error(err);
        throw err;
      }
    },
    [ensureClientSecret, selectedAssetId, handleSelectAsset]
  );

  // --- Conversation handlers ---

  const handleSelectConversation = useCallback(
    (id: string) => {
      loadConversation(id);
    },
    [loadConversation]
  );

  const handleNewConversation = useCallback(() => {
    clearMessages();
  }, [clearMessages]);

  return (
    <div className="h-full w-full overflow-hidden bg-background relative">
      {/* Read-only badge */}
      {isReadOnly && (
        <div className="absolute top-4 right-4 z-40">
          <Badge
            variant="secondary"
            className="bg-amber-100 text-amber-800 border-amber-200"
          >
            閲覧専用
          </Badge>
        </div>
      )}

      {/* Manage dialog */}
      <Dialog open={showManageDialog} onOpenChange={setShowManageDialog}>
        <DialogContent className="max-w-6xl max-h-[90vh] p-6">
          <DialogHeader className="mb-4">
            <DialogTitle className="text-2xl font-bold">
              モデルアセット管理
            </DialogTitle>
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

      {/* Create asset dialog */}
      <Dialog open={showAssetDialog} onOpenChange={setShowAssetDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>モデルアセットを作成</DialogTitle>
          </DialogHeader>
          <ModelAssetForm
            onSubmit={handleSaveAsset}
            loading={savingAsset}
            submitLabel="作成"
          />
        </DialogContent>
      </Dialog>

      {/* Share dialog */}
      <ShareDialog
        open={showShareDialog}
        onOpenChange={setShowShareDialog}
        shareInfo={shareInfo}
        isLoading={shareLoading}
        onToggleShare={handleToggleShare}
      />

      {/* History panel */}
      <HistoryPanel
        open={showHistory}
        onOpenChange={setShowHistory}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        ensureClientSecret={ensureClientSecret}
      />

      {/* Header bar */}
      <div className="absolute top-0 left-0 right-0 z-30 h-12 bg-background/80 backdrop-blur border-b border-[#e5e7eb] flex items-center px-3 sm:px-4 gap-2">
        <button
          onClick={() => setShowHistory(true)}
          className="p-2 rounded-lg hover:bg-[#f0f1f5] transition-colors cursor-pointer"
          aria-label="会話履歴"
        >
          <History className="w-4 h-4 text-[#6b7280]" />
        </button>

        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-foreground truncate">
            マーケティング AI
          </h1>
        </div>

        <div className="flex items-center gap-1">
          {currentConversationId && (
            <button
              onClick={() => setShowShareDialog(true)}
              className="p-2 rounded-lg hover:bg-[#f0f1f5] transition-colors cursor-pointer"
              aria-label="共有"
            >
              <Share2 className="w-4 h-4 text-[#6b7280]" />
            </button>
          )}
          <button
            onClick={() => setShowManageDialog(true)}
            className="p-2 rounded-lg hover:bg-[#f0f1f5] transition-colors cursor-pointer"
            aria-label="設定"
          >
            <Settings className="w-4 h-4 text-[#6b7280]" />
          </button>
        </div>
      </div>

      {/* Main chat area */}
      <div className="h-full pt-12">
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          onSend={sendMessage}
          onStop={stopStreaming}
          disabled={isReadOnly}
          assets={assets}
          selectedAssetId={selectedAssetId}
          onAssetChange={handleSelectAsset}
          pendingQuestionGroup={pendingQuestionGroup}
          onRespondToQuestions={respondToQuestions}
        />
      </div>

      {/* Read-only overlay */}
      {isReadOnly && (
        <div className="absolute bottom-0 left-0 right-0 h-32 z-20 pointer-events-auto bg-gradient-to-t from-white via-white/95 to-transparent flex items-end justify-center pb-4">
          <div className="text-center px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg shadow-sm">
            <p className="text-sm text-amber-800">
              この会話は共有されています。閲覧のみ可能です。
            </p>
          </div>
        </div>
      )}

      {/* Attachment panel */}
      {attachments.length > 0 && (
        <>
          <div className="absolute bottom-4 right-4 z-30">
            <button
              type="button"
              onClick={() => setShowAttachments((v) => !v)}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-full bg-[var(--brand-400)] text-white shadow-lg hover:bg-[#176d80] focus:outline-none focus:ring-2 focus:ring-[var(--brand-300)] cursor-pointer"
            >
              <Download className="h-4 w-4" />
              添付 {attachments.length} 件
            </button>
          </div>
          <div
            className={`absolute bottom-16 right-4 z-30 w-80 max-w-[92vw] transition-all duration-200 ${
              showAttachments
                ? "opacity-100 translate-y-0"
                : "opacity-0 pointer-events-none translate-y-2"
            }`}
          >
            <div className="bg-white/95 backdrop-blur rounded-xl shadow-2xl border border-[#e5e7eb] max-h-[55vh] overflow-y-auto">
              <div className="px-4 py-3 border-b flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur rounded-t-xl">
                <div className="text-sm font-semibold text-foreground">
                  添付ファイル
                </div>
                <button
                  type="button"
                  className="text-xs text-[#6b7280] hover:text-foreground cursor-pointer"
                  onClick={() => setShowAttachments(false)}
                >
                  閉じる
                </button>
              </div>
              <ul className="divide-y divide-[#f0f1f5]">
                {attachments.map((att) => (
                  <li key={`${att.message_id}-${att.file_id}`}>
                    <a
                      href={att.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start gap-3 px-4 py-3 hover:bg-[#f0f1f5] transition"
                      download
                    >
                      <div className="mt-0.5">
                        <Download className="h-4 w-4 text-[var(--brand-400)]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-foreground truncate">
                          {att.filename || att.file_id}
                        </div>
                        {att.created_at && (
                          <div className="text-xs text-[#9ca3af]">
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
  );
}
