"use client";

/**
 * Marketing Chat Component (V2 - ADK/Gemini)
 *
 * Clean, editorial-style chat interface using shadcn/ui components.
 * Full-stack mode with all agents enabled by default.
 */

import { useCallback, forwardRef, useImperativeHandle, useState, useEffect, useRef } from "react";
import { useMarketingChat } from "@/hooks/use-marketing-chat-v2";
import { useFeedback } from "@/hooks/use-feedback";
import { FeedbackModeToggle } from "@/components/feedback/FeedbackModeToggle";
import { AnnotationPanel } from "@/components/feedback/AnnotationPanel";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";
import { SuggestionCarousel } from "./SuggestionCarousel";
import type { Suggestion } from "./SuggestionCarousel";
import { AgentShowcase } from "./AgentShowcase";
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
  Mail,
  Calendar,
  Globe,
  Code2,
  Megaphone,
  FileText,
  Menu,
} from "lucide-react";
import { SidebarTrigger } from "@/components/ui/sidebar";
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
  getClientSecret?: () => string | null;
}

export interface MarketingChatRef {
  clearMessages: () => void;
  loadConversation: (id: string) => Promise<void>;
}

// Empty state suggestions - comprehensive queries covering all agents
const ALL_SUGGESTIONS: Suggestion[] = [
  // --- GA4 / Analytics ---
  {
    icon: TrendingUp,
    tag: "GA4",
    text: "今週のGA4流入から求職者の応募・入社までのファネル全体を分析して、改善ポイントを教えて",
  },
  {
    icon: TrendingUp,
    tag: "GA4",
    text: "hitocareerとachievehrの直近1ヶ月のセッション・PV・直帰率を比較して、トレンドをチャートで見せて",
  },
  {
    icon: TrendingUp,
    tag: "GSC",
    text: "hitocareer.comの検索パフォーマンス（クリック数・表示回数・CTR・平均順位）を過去3ヶ月で分析して",
  },
  // --- SEO ---
  {
    icon: Search,
    tag: "SEO",
    text: "hitocareer.comと競合3社のSEO状況（DR、被リンク、オーガニックKW）を比較分析して",
  },
  {
    icon: Search,
    tag: "SEO",
    text: "hitocareer.comで順位が下がっているキーワードを特定して、改善優先度をつけて",
  },
  // --- 広告 ---
  {
    icon: Megaphone,
    tag: "Meta広告",
    text: "現在配信中のMeta広告キャンペーンのCTR・CPA・ROASを一覧にして、改善すべきものを特定して",
  },
  {
    icon: Megaphone,
    tag: "Meta広告",
    text: "「人材紹介 転職」関連のインタレストターゲティングで、推定オーディエンスサイズを調べて",
  },
  // --- CRM ---
  {
    icon: BarChart3,
    tag: "CRM",
    text: "過去3ヶ月のチャネル別（Indeed, doda, 自然流入）の獲得単価と入社率を比較して",
  },
  {
    icon: BarChart3,
    tag: "CRM",
    text: "今月の担当者別パフォーマンス（面談数・内定率・入社率）をランキング形式で見せて",
  },
  {
    icon: BarChart3,
    tag: "CRM",
    text: "直近3ヶ月のステータス別ファネル（応募→面談→内定→入社）をチャネルごとに比較して",
  },
  // --- 企業DB ---
  {
    icon: Building2,
    tag: "企業DB",
    text: "35歳、年収希望600万、成長志向の候補者に合う企業TOP5と、それぞれの訴求ポイントを提案して",
  },
  {
    icon: Building2,
    tag: "企業DB",
    text: "リモートワーク可能でワークライフバランスが良い企業を検索して、年収レンジ付きで一覧にして",
  },
  {
    icon: Building2,
    tag: "企業DB",
    text: "株式会社MyVisionと他2社を比較して、年収・採用要件・訴求ポイントの違いを表にまとめて",
  },
  // --- CA支援 ---
  {
    icon: AlertTriangle,
    tag: "CA支援",
    text: "今週面談予定の候補者で、競合エージェントリスクが高い人を洗い出して面談準備資料を作って",
  },
  {
    icon: AlertTriangle,
    tag: "CA支援",
    text: "山田さん（Zoho ID）の面談準備をして。候補者情報・議事録・おすすめ企業を一括でまとめて",
  },
  {
    icon: AlertTriangle,
    tag: "CA支援",
    text: "緊急度が高い候補者を洗い出して、それぞれに対抗提案できる企業を3社ずつ提案して",
  },
  // --- Gmail ---
  {
    icon: Mail,
    tag: "Gmail",
    text: "今日届いた未読メールを一覧で見せて。重要なものがあればハイライトして",
  },
  {
    icon: Mail,
    tag: "Gmail",
    text: "田中さんからの直近1週間のメールを検索して、やり取りの流れをまとめて",
  },
  {
    icon: Mail,
    tag: "Gmail",
    text: "「面談」に関するメールスレッドを検索して、直近のやり取りを要約して",
  },
  // --- Calendar ---
  {
    icon: Calendar,
    tag: "カレンダー",
    text: "今日と明日の予定を一覧で教えて。Google Meetリンクがあれば一緒に表示して",
  },
  {
    icon: Calendar,
    tag: "カレンダー",
    text: "来週のスケジュールを曜日ごとに整理して、面談系の予定をピックアップして",
  },
  // --- Google検索 ---
  {
    icon: Globe,
    tag: "Web検索",
    text: "人材紹介業界の最新トレンドと法改正を調べて、自社への影響をまとめて",
  },
  {
    icon: Globe,
    tag: "Web検索",
    text: "競合の人材紹介会社の最新ニュースや動向を調べて教えて",
  },
  // --- コード実行 ---
  {
    icon: Code2,
    tag: "計算",
    text: "過去6ヶ月の月次データから成長率を計算して、来月の予測値をシミュレーションして",
  },
  // --- WordPress ---
  {
    icon: FileText,
    tag: "WordPress",
    text: "hitocareerブログの最新記事一覧を取得して、SEO要件を満たしているかチェックして",
  },
  // --- 統合分析 ---
  {
    icon: Users,
    tag: "統合分析",
    text: "今月の流入→応募→面談→内定→入社の全体ファネルと、離脱が多いステップの改善案を提示して",
  },
  {
    icon: Users,
    tag: "統合分析",
    text: "Indeed経由の候補者の特徴を分析して、マッチしやすい企業の傾向と効果的な訴求ポイントを教えて",
  },
  {
    icon: Users,
    tag: "統合分析",
    text: "今日の予定と未読メールを確認しつつ、対応が必要な候補者をCRMから洗い出して",
  },
  {
    icon: Users,
    tag: "統合分析",
    text: "SEOトラフィックとCRMの応募データを突合して、コンテンツ→応募の転換率が高いページを特定して",
  },
];

function EmptyState({ onSend }: { onSend: (msg: string) => void }) {
  const [showShowcase, setShowShowcase] = useState(false);

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
        <p className="text-[12.5px] text-muted-foreground/80 max-w-md leading-relaxed">
          11人のエージェントと150以上のツールを搭載した、GA4・GSC・Zoho CRM・企業DB・Meta広告・Ahrefs・Gmail・カレンダー・Google検索・コード実行を横断できるマルチエージェントシステム。
        </p>
        <button
          onClick={() => setShowShowcase(true)}
          className="mt-2.5 inline-flex items-center gap-1 text-[11.5px] text-[#1e8aa0]/70 hover:text-[#1e8aa0] transition-colors cursor-pointer group"
        >
          <span className="underline underline-offset-2 decoration-[#1e8aa0]/25 group-hover:decoration-[#1e8aa0]/60">
            エージェント一覧を見る
          </span>
          <span className="text-[10px] opacity-60 group-hover:opacity-100 transition-opacity">&rarr;</span>
        </button>
      </div>

      {/* Suggestion carousel */}
      <SuggestionCarousel
        suggestions={ALL_SUGGESTIONS}
        onSend={onSend}
        perPage={6}
        interval={6000}
      />

      {/* Agent Showcase Dialog */}
      <AgentShowcase
        open={showShowcase}
        onOpenChange={setShowShowcase}
        onTryQuery={(query) => {
          setShowShowcase(false);
          onSend(query);
        }}
      />
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
      getClientSecret: getClientSecretProp,
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
      loadConversation,
    } = useMarketingChat({
      initialConversationId,
      onConversationChange,
    });

    // Feedback system
    const getClientSecretFn = useCallback(() => getClientSecretProp?.() || null, [getClientSecretProp]);
    const feedback = useFeedback(getClientSecretFn);
    const [activeAnnotationId, setActiveAnnotationId] = useState<string | null>(null);

    // Load feedback master data — retry until successful
    useEffect(() => {
      if (!getClientSecretProp) return;
      if (feedback.tags.length > 0) return; // already loaded
      const tryLoad = () => feedback.loadMasterData();
      tryLoad();
      // Retry after 2s if token wasn't ready on first call
      const timer = setTimeout(tryLoad, 2000);
      return () => clearTimeout(timer);
    }, [getClientSecretProp, feedback.tags.length]); // eslint-disable-line react-hooks/exhaustive-deps

    // Handle sidebar annotation click — scroll to message + flash highlight
    const handleSelectAnnotation = useCallback((annotationId: string, messageId: string) => {
      setActiveAnnotationId(annotationId);
      // Scroll the message into view
      const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
      if (msgEl) {
        msgEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, []);

    // Load feedback when conversation changes — with retry for token readiness
    useEffect(() => {
      if (!conversationId || !getClientSecretProp) {
        feedback.clearFeedback();
        return;
      }

      let cancelled = false;
      const tryLoad = (attempt: number) => {
        if (cancelled || attempt > 3) return;
        const secret = getClientSecretProp();
        if (!secret) {
          // Token not ready yet — retry with increasing delay
          setTimeout(() => tryLoad(attempt + 1), 1500 * (attempt + 1));
          return;
        }
        feedback.loadConversationFeedback(conversationId);
      };
      tryLoad(0);
      return () => { cancelled = true; };
    }, [conversationId]); // eslint-disable-line react-hooks/exhaustive-deps

    // Expose clearMessages and loadConversation via ref
    useImperativeHandle(ref, () => ({
      clearMessages,
      loadConversation,
    }), [clearMessages, loadConversation]);

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
          <header className="shrink-0 flex items-center justify-between h-14 px-2 sm:px-4 border-b border-border bg-background">
            {/* Left side - Title */}
            <div className="flex items-center gap-1.5 sm:gap-2">
              <SidebarTrigger className="md:hidden" />
              <Layers className="w-4 h-4 text-[#1e8aa0] hidden sm:block" strokeWidth={1.5} />
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

              {/* FB Mode Toggle */}
              {!isReadOnly && (
                <FeedbackModeToggle
                  isActive={feedback.isFeedbackMode}
                  onToggle={feedback.setIsFeedbackMode}
                />
              )}

              {/* More menu (attachments + overflow actions on mobile) */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon-sm">
                    <MoreHorizontal className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  {attachments.length > 0 && (
                    <DropdownMenuItem onClick={() => setShowAttachments(true)}>
                      <Download className="w-4 h-4 mr-2" />
                      添付ファイル ({attachments.length})
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          {/* Messages area + Annotation Panel */}
          <div className="flex-1 overflow-hidden flex min-h-0">
            {/* Main message column */}
            <div className="flex-1 overflow-hidden flex flex-col min-h-0">
              {messages.length === 0 ? (
                <div className="flex-1 overflow-y-auto">
                  <EmptyState onSend={handleSend} />
                </div>
              ) : (
                <MessageList
                  messages={messages}
                  isStreaming={isStreaming}
                  onSendMessage={handleSend}
                  feedbackByMessage={feedback.feedbackByMessage}
                  annotationsByMessage={feedback.annotationsByMessage}
                  feedbackTags={feedback.tags}
                  isFeedbackMode={feedback.isFeedbackMode}
                  conversationId={conversationId}
                  activeAnnotationId={activeAnnotationId}
                  onSubmitFeedback={feedback.submitFeedback}
                  onCreateAnnotation={feedback.createAnnotation}
                  onDeleteAnnotation={feedback.deleteAnnotation}
                  onSetActiveAnnotation={setActiveAnnotationId}
                />
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

            {/* Annotation sidebar — desktop: inline panel, mobile: Sheet overlay */}
            {feedback.isFeedbackMode && messages.length > 0 && (
              <AnnotationPanel
                messages={messages}
                feedbackByMessage={feedback.feedbackByMessage}
                annotationsByMessage={feedback.annotationsByMessage}
                activeAnnotationId={activeAnnotationId}
                onSelectAnnotation={handleSelectAnnotation}
                onDeleteAnnotation={feedback.deleteAnnotation}
                onClose={() => feedback.setIsFeedbackMode(false)}
              />
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
