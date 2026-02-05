"use client";

/**
 * Marketing Chat Component
 *
 * Clean, editorial-style chat interface using shadcn/ui components.
 * No duplicate headers or sidebars.
 */

import { useState, useCallback, useMemo, forwardRef, useImperativeHandle } from "react";
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
  History,
  MoreHorizontal,
  Sparkles,
  ChevronDown,
  Zap,
  Globe,
  Code,
  Check,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
  onHistoryClick?: () => void;
  shareInfo?: ShareInfo | null;
  attachments?: Attachment[];
  isReadOnly?: boolean;
  className?: string;
}

export interface MarketingChatRef {
  clearMessages: () => void;
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
      <div className="w-12 h-12 bg-primary/5 border border-primary/10 rounded-2xl flex items-center justify-center mb-5">
        <Sparkles className="w-6 h-6 text-primary/70" />
      </div>
      <h2 className="text-lg font-semibold text-foreground mb-1.5 tracking-tight">
        Marketing AI
      </h2>
      <p className="text-sm text-muted-foreground mb-8 max-w-md leading-relaxed">
        SEO、Analytics、CRM、広告データをAIで分析します
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-lg w-full">
        {SUGGESTIONS.map((s, i) => {
          const Icon = s.icon;
          return (
            <button
              key={i}
              onClick={() => onSend(s.text)}
              className="group text-left px-4 py-3.5 bg-background border border-border rounded-xl text-sm text-foreground hover:border-primary/30 hover:bg-accent/50 transition-all duration-200 cursor-pointer leading-relaxed flex items-start gap-3"
            >
              <Icon className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors mt-0.5 shrink-0" />
              <span>{s.text}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Model Selector Component
// ---------------------------------------------------------------------------

interface ModelSelectorProps {
  assets: ModelAsset[];
  selectedAssetId: string | null;
  onSelect: (id: string) => void;
  onSettingsClick?: () => void;
  disabled?: boolean;
}

function ModelSelector({
  assets,
  selectedAssetId,
  onSelect,
  onSettingsClick,
  disabled,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);

  const currentAsset = assets.find((a) => a.id === selectedAssetId);

  // Count tools for each asset
  const getToolCount = (asset: ModelAsset) => {
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
  };

  const currentToolCount = currentAsset ? getToolCount(currentAsset) : 0;

  // Get tool badges for an asset
  const getToolBadges = (asset: ModelAsset) => {
    const tools: { name: string; enabled: boolean }[] = [
      { name: "Web", enabled: !!asset.enable_web_search },
      { name: "Code", enabled: !!asset.enable_code_interpreter },
      { name: "GA4", enabled: !!asset.enable_ga4 },
      { name: "GSC", enabled: !!asset.enable_gsc },
      { name: "Ahrefs", enabled: !!asset.enable_ahrefs },
      { name: "Meta", enabled: !!asset.enable_meta_ads },
      { name: "WP", enabled: !!asset.enable_wordpress },
      { name: "Zoho", enabled: !!asset.enable_zoho_crm },
    ];
    return tools.filter((t) => t.enabled);
  };

  return (
    <div className="flex items-center gap-1.5">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            disabled={disabled}
            className="group flex items-center gap-2 h-9 pl-3 pr-2 rounded-lg border border-border bg-background hover:bg-accent/50 hover:border-primary/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-primary/70" />
              <span className="text-sm font-medium text-foreground">
                {currentAsset?.name || "モデル"}
              </span>
              {currentToolCount > 0 && (
                <span className="flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-semibold bg-primary/10 text-primary rounded-full">
                  {currentToolCount}
                </span>
              )}
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground transition-colors" />
          </button>
        </PopoverTrigger>
        <PopoverContent
          align="start"
          className="w-72 p-1.5"
          sideOffset={8}
        >
          <div className="space-y-0.5 max-h-[300px] overflow-y-auto">
            {assets.map((asset) => {
              const isSelected = asset.id === selectedAssetId;
              const toolBadges = getToolBadges(asset);
              const toolCount = getToolCount(asset);

              return (
                <button
                  key={asset.id}
                  onClick={() => {
                    onSelect(asset.id);
                    setOpen(false);
                  }}
                  className={`
                    w-full text-left px-3 py-2.5 rounded-md transition-all duration-150
                    ${isSelected
                      ? "bg-primary/5 border border-primary/20"
                      : "hover:bg-accent border border-transparent"
                    }
                  `}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${isSelected ? "text-primary" : "text-foreground"}`}>
                        {asset.name}
                      </span>
                      {isSelected && (
                        <Check className="w-3.5 h-3.5 text-primary" />
                      )}
                    </div>
                    {toolCount > 0 && (
                      <span className="text-[10px] text-muted-foreground">
                        {toolCount} ツール
                      </span>
                    )}
                  </div>
                  {toolBadges.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {toolBadges.slice(0, 5).map((tool) => (
                        <span
                          key={tool.name}
                          className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium bg-muted text-muted-foreground rounded"
                        >
                          {tool.name}
                        </span>
                      ))}
                      {toolBadges.length > 5 && (
                        <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium bg-muted text-muted-foreground rounded">
                          +{toolBadges.length - 5}
                        </span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </PopoverContent>
      </Popover>

      {/* Settings button - right next to model selector */}
      {onSettingsClick && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onSettingsClick}
              className="text-muted-foreground hover:text-foreground"
            >
              <Settings className="w-4 h-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>モデル設定</TooltipContent>
        </Tooltip>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Chat Component
// ---------------------------------------------------------------------------

export const MarketingChat = forwardRef<MarketingChatRef, MarketingChatProps>(
  function MarketingChat(
    {
      initialConversationId,
      assets = [],
      selectedAssetId,
      onAssetSelect,
      onConversationChange,
      onSettingsClick,
      onShareClick,
      onHistoryClick,
      shareInfo,
      attachments = [],
      isReadOnly = false,
      className = "",
    },
    ref
  ) {
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

    // Expose clearMessages via ref
    useImperativeHandle(ref, () => ({
      clearMessages,
    }), [clearMessages]);

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

    return (
      <TooltipProvider>
        <div className={`flex flex-col h-full bg-background relative ${className}`}>
          {/* Read-only badge */}
          {isReadOnly && (
            <div className="absolute top-3 right-3 z-40">
              <Badge variant="secondary" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">
                閲覧のみ
              </Badge>
            </div>
          )}

          {/* Clean Header */}
          <header className="shrink-0 flex items-center justify-between h-14 px-4 border-b border-border bg-background">
            {/* Left side - Model selector + Settings */}
            <div className="flex items-center">
              {assets.length > 0 && (
                <ModelSelector
                  assets={assets}
                  selectedAssetId={effectiveAssetId}
                  onSelect={handleAssetSelect}
                  onSettingsClick={onSettingsClick}
                  disabled={isStreaming}
                />
              )}
            </div>

            {/* Right side - Actions */}
            <div className="flex items-center gap-0.5">
              {/* New chat button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={handleNewChat}
                    disabled={isStreaming || messages.length === 0}
                  >
                    <PlusCircle className="w-4 h-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>新規チャット</TooltipContent>
              </Tooltip>

              {/* History button */}
              {onHistoryClick && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={onHistoryClick}
                    >
                      <History className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>履歴</TooltipContent>
                </Tooltip>
              )}

              {/* Share button */}
              {onShareClick && conversationId && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant={shareInfo?.is_shared ? "secondary" : "ghost"}
                      size="icon-sm"
                      onClick={onShareClick}
                      className={shareInfo?.is_shared ? "text-blue-600" : ""}
                    >
                      <Share2 className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {shareInfo?.is_shared ? "共有中" : "共有"}
                  </TooltipContent>
                </Tooltip>
              )}

              {/* More menu (attachments only now) */}
              {attachments.length > 0 && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon-sm">
                      <MoreHorizontal className="w-4 h-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem onClick={() => setShowAttachments(true)}>
                      <Download className="w-4 h-4 mr-2" />
                      添付ファイル ({attachments.length})
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </header>

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
              <div className="mx-4 mb-2 p-3 bg-destructive/10 text-destructive rounded-lg border border-destructive/20 text-sm">
                {error}
              </div>
            )}
          </div>

          {/* Attachments panel */}
          {attachments.length > 0 && showAttachments && (
            <AttachmentsPanel
              attachments={attachments}
              onClose={() => setShowAttachments(false)}
            />
          )}

          {/* Read-only overlay */}
          {isReadOnly && (
            <div className="absolute bottom-0 left-0 right-0 h-28 z-20 pointer-events-auto bg-gradient-to-t from-background via-background/95 to-transparent flex items-end justify-center pb-4">
              <div className="text-center px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg">
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
      </TooltipProvider>
    );
  }
);

// ---------------------------------------------------------------------------
// Attachments Panel
// ---------------------------------------------------------------------------

interface AttachmentsPanelProps {
  attachments: Attachment[];
  onClose: () => void;
}

function AttachmentsPanel({ attachments, onClose }: AttachmentsPanelProps) {
  return (
    <div className="absolute inset-0 z-40 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-background border border-border rounded-xl shadow-lg w-full max-w-md max-h-[70vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-semibold">添付ファイル</h3>
          <Button variant="ghost" size="icon-sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* List */}
        <ul className="flex-1 overflow-y-auto divide-y divide-border">
          {attachments.map((att) => (
            <li key={`${att.message_id}-${att.file_id}`}>
              <a
                href={att.download_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-3 px-4 py-3 hover:bg-accent transition-colors"
                download
              >
                <Download className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">
                    {att.filename || att.file_id}
                  </div>
                  {att.created_at && (
                    <div className="text-xs text-muted-foreground">
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
  );
}
