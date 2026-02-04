"use client";

/**
 * Marketing Chat Component
 *
 * Native SSE streaming chat interface with ChatGPT-style UI.
 * Based on ga4-oauth-aiagent reference implementation.
 */

import { useState, useCallback, useMemo } from "react";
import { useMarketingChat } from "@/hooks/use-marketing-chat";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";
import {
  Settings,
  Share2,
  Download,
  X,
  PlusCircle,
  BarChart3,
  Search,
  TrendingUp,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ModelAsset as ModelAssetType } from "@/lib/marketing/types";

// Re-export for convenience
export type ModelAsset = ModelAssetType;

export type ShareInfo = {
  thread_id: string;
  is_shared: boolean;
  share_url: string | null;
  owner_email: string;
  is_owner: boolean;
};

export type Attachment = {
  file_id: string;
  filename?: string | null;
  container_id?: string | null;
  download_url: string;
  message_id?: string;
  created_at?: string | null;
};

export interface MarketingChatProps {
  initialConversationId?: string | null;
  assets?: ModelAsset[];
  selectedAssetId?: string | null;
  onAssetSelect?: (assetId: string) => void;
  onConversationChange?: (conversationId: string | null) => void;
  onSettingsClick?: () => void;
  onShareClick?: () => void;
  shareInfo?: ShareInfo | null;
  attachments?: Attachment[];
  isReadOnly?: boolean;
  className?: string;
}

// Empty state suggestions
const SUGGESTIONS = [
  {
    icon: TrendingUp,
    text: "先週のチャネル別流入数を分析して",
  },
  {
    icon: Search,
    text: "SEOのパフォーマンスを確認したい",
  },
  {
    icon: BarChart3,
    text: "今月の求職者データを教えて",
  },
  {
    icon: Users,
    text: "入社率が高いチャネルはどれ？",
  },
];

function EmptyState({ onSend }: { onSend: (msg: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4 sm:px-8">
      <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-[#1a1a2e] to-[#2a2a4e] rounded-xl flex items-center justify-center mb-4 sm:mb-5 shadow-lg shadow-[#1a1a2e]/10">
        <BarChart3 className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
      </div>
      <h2 className="text-base sm:text-lg font-bold text-[#1a1a2e] mb-1 sm:mb-1.5 tracking-tight">
        Marketing AI Assistant
      </h2>
      <p className="text-xs sm:text-sm text-[#6b7280] mb-6 sm:mb-8 max-w-md leading-relaxed">
        SEO、Analytics、CRM、広告データをAIで分析します。何でも聞いてください。
      </p>
      <div className="grid grid-cols-2 gap-2 sm:gap-2.5 max-w-md w-full">
        {SUGGESTIONS.map((s, i) => {
          const Icon = s.icon;
          return (
            <button
              key={i}
              onClick={() => onSend(s.text)}
              className="group text-left px-3 sm:px-3.5 py-2.5 sm:py-3 bg-white border border-[#e5e7eb] rounded-xl text-xs text-[#374151] hover:border-[#1a1a2e]/20 hover:shadow-sm transition-all duration-200 cursor-pointer leading-relaxed flex items-start gap-2 sm:gap-2.5"
            >
              <Icon className="w-3.5 h-3.5 text-[#9ca3af] group-hover:text-[#e94560] transition-colors mt-0.5 shrink-0" />
              <span>{s.text}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function MarketingChat({
  initialConversationId,
  assets = [],
  selectedAssetId,
  onAssetSelect,
  onConversationChange,
  onSettingsClick,
  onShareClick,
  shareInfo,
  attachments = [],
  isReadOnly = false,
  className = "",
}: MarketingChatProps) {
  const [internalAssetId, setInternalAssetId] = useState<string | null>(
    selectedAssetId ?? (assets.length > 0 ? assets[0].id : null)
  );
  const [showAttachments, setShowAttachments] = useState(false);

  const effectiveAssetId = selectedAssetId ?? internalAssetId;

  const handleAssetSelect = useCallback(
    (assetId: string) => {
      setInternalAssetId(assetId);
      onAssetSelect?.(assetId);
    },
    [onAssetSelect]
  );

  const {
    messages,
    isStreaming,
    error,
    conversationId,
    sendMessage,
    clearMessages,
  } = useMarketingChat({
    initialConversationId,
    selectedAssetId: effectiveAssetId,
    onConversationChange,
  });

  const handleSend = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreaming || isReadOnly) return;
      await sendMessage(content);
    },
    [sendMessage, isStreaming, isReadOnly]
  );

  const handleNewChat = useCallback(() => {
    clearMessages();
  }, [clearMessages]);

  // Count enabled tools for display
  const toolCount = useMemo(() => {
    const asset = assets.find((a) => a.id === effectiveAssetId);
    if (!asset) return 0;
    let count = 0;
    if (asset.enable_web_search) count++;
    if (asset.enable_code_interpreter) count++;
    if (asset.enable_ga4) count++;
    if (asset.enable_meta_ads) count++;
    if (asset.enable_gsc) count++;
    if (asset.enable_ahrefs) count++;
    if (asset.enable_wordpress) count++;
    if (asset.enable_zoho_crm) count++;
    return count;
  }, [assets, effectiveAssetId]);

  return (
    <div className={`flex flex-col h-full bg-[#f8f9fb] relative ${className}`}>
      {/* Read-only badge */}
      {isReadOnly && (
        <div className="absolute top-4 right-4 z-40">
          <Badge variant="secondary" className="bg-amber-100 text-amber-800 border-amber-200">
            閲覧のみ
          </Badge>
        </div>
      )}

      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-3 sm:px-6 py-2.5 sm:py-3 bg-white border-b border-[#e5e7eb]">
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Settings button */}
          {onSettingsClick && (
            <button
              onClick={onSettingsClick}
              className="p-2 rounded-lg hover:bg-[#f0f1f5] transition-colors"
              title="設定"
            >
              <Settings className="w-4 h-4 sm:w-5 sm:h-5 text-[#6b7280]" />
            </button>
          )}
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 sm:w-8 sm:h-8 bg-gradient-to-br from-[#1a1a2e] to-[#2a2a4e] rounded-lg flex items-center justify-center">
              <BarChart3 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
            </div>
            <span className="text-sm sm:text-base font-semibold text-[#1a1a2e] hidden sm:inline">
              Marketing AI
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Model selector */}
          {assets.length > 0 && (
            <select
              value={effectiveAssetId ?? ""}
              onChange={(e) => handleAssetSelect(e.target.value)}
              className="text-xs sm:text-sm px-2 sm:px-3 py-1.5 border border-[#d1d5db] rounded-lg bg-white text-[#1a1a2e] focus:outline-none focus:ring-2 focus:ring-[#1a1a2e]/20 focus:border-[#1a1a2e] transition-all"
              disabled={isStreaming}
            >
              {assets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.name}
                  {asset.id === effectiveAssetId && toolCount > 0
                    ? ` (${toolCount})`
                    : ""}
                </option>
              ))}
            </select>
          )}

          {/* Share button */}
          {onShareClick && conversationId && (
            <button
              onClick={onShareClick}
              className={`p-2 rounded-lg transition-colors ${
                shareInfo?.is_shared
                  ? "bg-blue-100 text-blue-700 hover:bg-blue-200"
                  : "hover:bg-[#f0f1f5] text-[#6b7280]"
              }`}
              title={shareInfo?.is_shared ? "共有中" : "共有"}
            >
              <Share2 className="w-4 h-4 sm:w-5 sm:h-5" />
            </button>
          )}

          {/* New chat button */}
          <button
            onClick={handleNewChat}
            disabled={isStreaming || messages.length === 0}
            className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs sm:text-sm font-medium border border-[#d1d5db] rounded-lg hover:bg-[#f0f1f5] disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-[#374151]"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">新規チャット</span>
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        {messages.length === 0 ? (
          <div className="flex-1 overflow-y-auto">
            <EmptyState onSend={handleSend} />
          </div>
        ) : (
          <MessageList messages={messages} isStreaming={isStreaming} />
        )}

        {/* Error display */}
        {error && (
          <div className="mx-4 sm:mx-6 mb-2 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Attachments panel */}
      {attachments.length > 0 && (
        <AttachmentsPanel
          attachments={attachments}
          show={showAttachments}
          onToggle={() => setShowAttachments((v) => !v)}
        />
      )}

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

      {/* Composer */}
      {!isReadOnly && (
        <Composer
          onSend={handleSend}
          isStreaming={isStreaming}
          disabled={isStreaming}
          placeholder="マーケティングデータについて質問..."
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Attachments Panel
// ---------------------------------------------------------------------------

interface AttachmentsPanelProps {
  attachments: Attachment[];
  show: boolean;
  onToggle: () => void;
}

function AttachmentsPanel({ attachments, show, onToggle }: AttachmentsPanelProps) {
  return (
    <>
      {/* Toggle button */}
      <div className="absolute bottom-20 right-4 z-30">
        <button
          type="button"
          onClick={onToggle}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-full bg-[#1a1a2e] text-white shadow-lg hover:bg-[#2a2a4e] focus:outline-none focus:ring-2 focus:ring-[#1a1a2e]/50 transition-colors"
        >
          <Download className="h-4 w-4" />
          添付ファイル ({attachments.length})
        </button>
      </div>

      {/* Panel */}
      <div
        className={`absolute bottom-32 right-4 z-30 w-80 max-w-[92vw] transition-all duration-200 ${
          show
            ? "opacity-100 translate-y-0"
            : "opacity-0 pointer-events-none translate-y-2"
        }`}
      >
        <div className="bg-white/95 backdrop-blur rounded-xl shadow-2xl border border-[#e5e7eb] max-h-[55vh] overflow-y-auto">
          <div className="px-4 py-3 border-b border-[#e5e7eb] flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur rounded-t-xl">
            <div className="text-sm font-semibold text-[#1a1a2e]">
              添付ファイル
            </div>
            <button
              type="button"
              className="p-1 hover:bg-[#f0f1f5] rounded transition-colors"
              onClick={onToggle}
            >
              <X className="h-4 w-4 text-[#6b7280]" />
            </button>
          </div>
          <ul className="divide-y divide-[#f0f1f5]">
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
                    <Download className="h-4 w-4 text-[#3b82f6]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-[#1a1a2e] truncate">
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
  );
}
