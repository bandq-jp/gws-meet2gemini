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
  Sparkles,
  Building2,
  AlertTriangle,
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
    text: "今週のGA4流入から求職者の応募・入社までのファネル全体を分析して、改善ポイントを教えて",
  },
  {
    icon: Building2,
    text: "35歳、年収希望600万、成長志向の候補者に合う企業TOP5と、それぞれの訴求ポイントを提案して",
  },
  {
    icon: Search,
    text: "hitocareer.comと競合3社のSEO状況（DR、被リンク、オーガニックKW）を比較分析して",
  },
  {
    icon: AlertTriangle,
    text: "今週面談予定の候補者で、競合エージェントリスクが高い人を洗い出して面談準備資料を作って",
  },
  {
    icon: BarChart3,
    text: "過去3ヶ月のチャネル別（Indeed, doda, 自然流入）の獲得単価と入社率を比較して",
  },
  {
    icon: Users,
    text: "今月の流入→応募→面談→内定→入社の全体ファネルと、離脱が多いステップの改善案を提示して",
  },
];

function EmptyState({ onSend }: { onSend: (msg: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4 sm:px-8">
      <div className="w-12 h-12 bg-primary/5 border border-primary/10 rounded-2xl flex items-center justify-center mb-5">
        <Sparkles className="w-6 h-6 text-primary/70" />
      </div>
      <h2 className="text-lg font-semibold text-foreground mb-1.5 tracking-tight">
        b&q エージェント
      </h2>
      <p className="text-sm text-muted-foreground mb-8 max-w-md leading-relaxed">
        マーケティング・採用・候補者支援をAIで統合分析。GA4、SEO、CRM、企業DB、広告データを横断して最適解を導きます
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-2xl w-full">
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
            {/* Left side - Title */}
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary/70" />
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
