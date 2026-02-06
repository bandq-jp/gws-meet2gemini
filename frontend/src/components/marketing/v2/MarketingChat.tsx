"use client";

/**
 * Marketing Chat Component (V2 - ADK/Gemini)
 *
 * Clean, editorial-style chat interface using shadcn/ui components.
 * Full-stack mode with all agents enabled by default.
 */

import { useCallback, forwardRef, useImperativeHandle, useState } from "react";
import { useMarketingChat } from "@/hooks/use-marketing-chat-v2";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";
import {
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
  Building2,
  AlertTriangle,
  Layers,
  ArrowRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

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
  onConversationChange?: (conversationId: string | null) => void;
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

// Empty state suggestions - comprehensive queries covering all agents
const SUGGESTIONS = [
  {
    icon: TrendingUp,
    tag: "GA4",
    text: "今週のGA4流入から求職者の応募・入社までのファネル全体を分析して、改善ポイントを教えて",
  },
  {
    icon: Building2,
    tag: "企業DB",
    text: "35歳、年収希望600万、成長志向の候補者に合う企業TOP5と、それぞれの訴求ポイントを提案して",
  },
  {
    icon: Search,
    tag: "SEO",
    text: "hitocareer.comと競合3社のSEO状況（DR、被リンク、オーガニックKW）を比較分析して",
  },
  {
    icon: AlertTriangle,
    tag: "CA支援",
    text: "今週面談予定の候補者で、競合エージェントリスクが高い人を洗い出して面談準備資料を作って",
  },
  {
    icon: BarChart3,
    tag: "CRM",
    text: "過去3ヶ月のチャネル別（Indeed, doda, 自然流入）の獲得単価と入社率を比較して",
  },
  {
    icon: Users,
    tag: "統合分析",
    text: "今月の流入→応募→面談→内定→入社の全体ファネルと、離脱が多いステップの改善案を提示して",
  },
];

function EmptyState({ onSend }: { onSend: (msg: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 sm:px-8">
      {/* Brand mark */}
      <div className="relative mb-6">
        <div className="w-10 h-10 rounded-xl bg-[#1e8aa0]/[0.07] flex items-center justify-center">
          <Layers className="w-5 h-5 text-[#1e8aa0]" strokeWidth={1.5} />
        </div>
        <div className="absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full bg-[#1e8aa0]/20 border-2 border-background" />
      </div>

      {/* Title cluster */}
      <div className="text-center mb-8">
        <h2 className="text-[15px] font-semibold text-foreground tracking-tight mb-1">
          b&q エージェント
        </h2>
        <p className="text-[13px] text-muted-foreground/80 max-w-sm leading-relaxed">
          マーケティング・採用・候補者支援を横断分析
        </p>
      </div>

      {/* Suggestion cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-2xl w-full">
        {SUGGESTIONS.map((s, i) => {
          const Icon = s.icon;
          return (
            <button
              key={i}
              onClick={() => onSend(s.text)}
              className="group text-left pl-3.5 pr-3 py-3 bg-background border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] hover:border-[#1e8aa0]/25 hover:bg-[#f8fbfc] transition-all duration-150 cursor-pointer leading-relaxed flex items-start gap-3"
            >
              <div className="shrink-0 mt-0.5">
                <Icon className="w-3.5 h-3.5 text-[#9ca3af] group-hover:text-[#1e8aa0] transition-colors" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="text-[10px] font-medium tracking-wide text-[#1e8aa0]/60 uppercase">{s.tag}</span>
                </div>
                <span className="line-clamp-2">{s.text}</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-[#d1d5db] group-hover:text-[#1e8aa0]/50 transition-colors shrink-0 mt-0.5 opacity-0 group-hover:opacity-100" />
            </button>
          );
        })}
      </div>
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
      onConversationChange,
      onShareClick,
      onHistoryClick,
      shareInfo,
      attachments = [],
      isReadOnly = false,
      className = "",
    },
    ref
  ) {
    const [showAttachments, setShowAttachments] = useState(false);

    const {
      messages,
      isStreaming,
      error,
      conversationId,
      sendMessage,
      cancelStream,
      clearMessages,
    } = useMarketingChat({
      initialConversationId,
      onConversationChange,
    });

    // Expose clearMessages via ref
    useImperativeHandle(ref, () => ({
      clearMessages,
    }), [clearMessages]);

    const handleSend = useCallback(
      async (content: string, files?: File[]) => {
        if ((!content.trim() && (!files || files.length === 0)) || isStreaming || isReadOnly) return;
        await sendMessage(content, files);
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
            {/* Left side - Title */}
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#1e8aa0]" strokeWidth={1.5} />
              <span className="text-sm font-medium text-foreground">b&q エージェント</span>
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

            {/* Error display (U-5: user-friendly messages with retry) */}
            {error && (
              <div className="mx-4 mb-2 p-3 bg-destructive/10 text-destructive rounded-lg border border-destructive/20 text-sm flex items-center justify-between gap-2">
                <span>{error.includes("fetch") || error.includes("network") ? "ネットワークエラーが発生しました" : error.length > 100 ? "エラーが発生しました。もう一度お試しください。" : error}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => { /* clear error by sending empty */ }}
                  className="shrink-0 text-xs text-destructive hover:text-destructive"
                >
                  閉じる
                </Button>
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
              onStop={cancelStream}
              isStreaming={isStreaming}
              disabled={isStreaming}
              placeholder="マーケティング・採用・候補者支援について質問..."
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
