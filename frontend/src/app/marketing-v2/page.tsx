"use client";

/**
 * Marketing AI Chat Page (V2 - Google ADK + Gemini)
 *
 * Clean, editorial-style chat interface.
 * Full-stack mode with all agents and tools enabled by default.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  MarketingChat,
  type ShareInfo,
  type Attachment,
  type MarketingChatRef,
} from "@/components/marketing/v2/MarketingChat";
import { ShareDialog } from "@/components/marketing/share-dialog";
import { HistoryPanel, type Conversation } from "@/components/marketing/v2/HistoryPanel";

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

  // Initial load
  useEffect(() => {
    loadAttachments(initialThreadId);
    loadShareStatus(initialThreadId);
  }, [initialThreadId, loadAttachments, loadShareStatus]);

  return (
    <>
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

      {/* Main Chat - Full height */}
      <MarketingChat
        ref={chatRef}
        initialConversationId={initialThreadId}
        onConversationChange={handleConversationChange}
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
