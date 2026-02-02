"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import type {
  Message,
  ModelAsset,
  PendingQuestionGroup,
} from "@/lib/marketing-types";
import { BarChart3, Search, Zap, TrendingUp } from "lucide-react";

interface Props {
  messages: Message[];
  isStreaming: boolean;
  onSend: (message: string, modelAssetId: string) => void;
  onStop: () => void;
  disabled?: boolean;
  assets?: ModelAsset[];
  selectedAssetId?: string;
  onAssetChange?: (id: string) => void;
  pendingQuestionGroup?: PendingQuestionGroup | null;
  onRespondToQuestions?: (
    groupId: string,
    responses: Record<string, string>
  ) => void;
}

function EmptyState({ onSend }: { onSend: (msg: string) => void }) {
  const suggestions = [
    {
      icon: TrendingUp,
      text: "過去7日間のアクセス状況をまとめて",
    },
    {
      icon: Search,
      text: "SEOのパフォーマンスを分析して",
    },
    {
      icon: BarChart3,
      text: "今月のトップページを教えて",
    },
    {
      icon: Zap,
      text: "改善アクションを提案して",
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4 sm:px-8">
      <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-[var(--brand-400)] to-[#176d80] rounded-xl flex items-center justify-center mb-4 sm:mb-5 shadow-lg shadow-[var(--brand-400)]/10">
        <BarChart3 className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
      </div>
      <h2 className="text-base sm:text-lg font-bold text-foreground mb-1 sm:mb-1.5 tracking-tight">
        マーケティング AI アシスタント
      </h2>
      <p className="text-xs sm:text-sm text-[#6b7280] mb-6 sm:mb-8 max-w-md leading-relaxed">
        GA4・Search Console・広告データをもとに分析します。何でも聞いてください。
      </p>
      <div className="grid grid-cols-2 gap-2 sm:gap-2.5 max-w-md w-full">
        {suggestions.map((s, i) => {
          const Icon = s.icon;
          return (
            <button
              key={i}
              onClick={() => onSend(s.text)}
              className="group text-left px-3 sm:px-3.5 py-2.5 sm:py-3 bg-white border border-[#e5e7eb] rounded-xl text-xs text-[#374151] hover:border-[var(--brand-400)]/30 hover:shadow-sm transition-all duration-200 cursor-pointer leading-relaxed flex items-start gap-2 sm:gap-2.5"
            >
              <Icon className="w-3.5 h-3.5 text-[#9ca3af] group-hover:text-[var(--brand-400)] transition-colors mt-0.5 shrink-0" />
              <span>{s.text}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function ChatWindow({
  messages,
  isStreaming,
  onSend,
  onStop,
  disabled,
  assets,
  selectedAssetId,
  onAssetChange,
  pendingQuestionGroup,
  onRespondToQuestions,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      const el = scrollRef.current;
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  const handleEmptySend = (msg: string) => {
    onSend(msg, selectedAssetId || "standard");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden">
        {messages.length === 0 ? (
          <EmptyState onSend={handleEmptySend} />
        ) : (
          <div className="max-w-3xl mx-auto py-4 sm:py-6 px-4 sm:px-6 space-y-5 sm:space-y-6 min-w-0">
            {messages.map((msg, idx) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                pendingQuestionGroup={
                  msg.isStreaming || idx === messages.length - 1
                    ? pendingQuestionGroup
                    : undefined
                }
                onRespondToQuestions={onRespondToQuestions}
              />
            ))}
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput
        onSend={onSend}
        isStreaming={isStreaming}
        onStop={onStop}
        disabled={disabled}
        assets={assets}
        selectedAssetId={selectedAssetId}
        onAssetChange={onAssetChange}
      />
    </div>
  );
}
