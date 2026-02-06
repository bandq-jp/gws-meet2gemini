"use client";

/**
 * HistoryPanel - Conversation history sidebar (ChatGPT/Claude style)
 *
 * Features:
 * - Right sheet that slides in
 * - Date grouping (Today, Yesterday, Past 7 days, Earlier)
 * - Delete with hover reveal
 * - Relative date formatting
 */

import { useState, useEffect, useCallback } from "react";
import {
  MessageSquare,
  Trash2,
  Loader2,
  X,
  Clock,
} from "lucide-react";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";

export interface Conversation {
  id: string;
  title: string;
  status?: string;
  created_at: string;
  updated_at: string;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentConversationId: string | null;
  onSelectConversation: (conv: Conversation) => void;
  onNewConversation: () => void;
  refreshTrigger?: number;
  getClientSecret: () => Promise<string>;
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "今";
  if (diffMins < 60) return `${diffMins}分前`;
  if (diffHours < 24) return `${diffHours}時間前`;
  if (diffDays < 7) return `${diffDays}日前`;
  return date.toLocaleDateString("ja-JP", { month: "short", day: "numeric" });
}

function ConversationItem({
  conv,
  active,
  onSelect,
  onDelete,
}: {
  conv: Conversation;
  active: boolean;
  onSelect: () => void;
  onDelete: (e: React.MouseEvent) => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onSelect();
      }}
      className={`
        group relative flex flex-col gap-0.5 px-3 py-2.5 rounded-xl
        transition-all duration-150 cursor-pointer
        ${
          active
            ? "bg-[#1a1a2e]/5 ring-1 ring-[#1a1a2e]/10"
            : "hover:bg-[#f0f1f5]"
        }
      `}
    >
      <div className="flex items-start gap-2.5">
        <MessageSquare
          className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${
            active ? "text-[#1a1a2e]" : "text-[#c4c7cc]"
          }`}
        />
        <span
          className={`text-[13px] leading-snug line-clamp-2 flex-1 ${
            active ? "text-[#1a1a2e] font-medium" : "text-[#4b5563]"
          }`}
        >
          {conv.title}
        </span>
        <button
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 p-1 -m-1 rounded-md
            hover:bg-[#fee2e2] hover:text-[#dc2626] text-[#9ca3af]
            transition-all duration-150 cursor-pointer shrink-0"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>
      <span className="text-[10px] text-[#b0b3b8] ml-6">
        {formatRelativeDate(conv.updated_at || conv.created_at)}
      </span>
    </div>
  );
}

export function HistoryPanel({
  open,
  onOpenChange,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  refreshTrigger,
  getClientSecret,
}: Props) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const loadConversations = useCallback(async () => {
    try {
      setLoading(true);
      const secret = await getClientSecret();
      const res = await fetch("/api/marketing-v2/threads", {
        headers: { "x-marketing-client-secret": secret },
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoading(false);
    }
  }, [getClientSecret]);

  useEffect(() => {
    if (open) {
      loadConversations();
    }
  }, [open, loadConversations, refreshTrigger]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const secret = await getClientSecret();
      const res = await fetch(`/api/marketing-v2/threads/${id}`, {
        method: "DELETE",
        headers: { "x-marketing-client-secret": secret },
      });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (currentConversationId === id) {
        onNewConversation();
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const handleSelect = (conv: Conversation) => {
    onSelectConversation(conv);
    onOpenChange(false);
  };

  // Group conversations by date
  const grouped = groupByDate(conversations);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="p-0 w-80 sm:w-96 flex flex-col bg-white border-l border-[#e5e7eb] [&>button:last-of-type]:hidden"
      >
        <SheetTitle className="sr-only">会話履歴</SheetTitle>

        {/* Header */}
        <div className="flex items-center justify-between px-4 h-14 shrink-0 border-b border-[#e5e7eb]">
          <div className="flex items-center gap-2.5">
            <Clock className="w-4 h-4 text-[#9ca3af]" />
            <span className="text-sm font-semibold text-[#1a1a2e] tracking-tight">
              履歴
            </span>
            {conversations.length > 0 && (
              <span className="text-[10px] font-medium text-[#9ca3af] bg-[#f0f1f5] rounded-full px-2 py-0.5">
                {conversations.length}
              </span>
            )}
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="w-8 h-8 flex items-center justify-center rounded-lg
              hover:bg-[#f0f1f5] text-[#9ca3af] hover:text-[#1a1a2e]
              transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto py-2 px-2">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-4 h-4 animate-spin text-[#9ca3af]" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-4">
              <div className="w-10 h-10 rounded-xl bg-[#f0f1f5] flex items-center justify-center mb-3">
                <MessageSquare className="w-5 h-5 text-[#c4c7cc]" />
              </div>
              <p className="text-sm text-[#9ca3af] text-center">
                まだ会話がありません
              </p>
              <p className="text-xs text-[#c4c7cc] text-center mt-1">
                チャットを始めると履歴がここに表示されます
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {grouped.map(({ label, items }) => (
                <div key={label}>
                  <div className="px-3 py-1.5">
                    <span className="text-[10px] font-semibold uppercase tracking-widest text-[#b0b3b8]">
                      {label}
                    </span>
                  </div>
                  <div className="space-y-0.5">
                    {items.map((conv) => (
                      <ConversationItem
                        key={conv.id}
                        conv={conv}
                        active={currentConversationId === conv.id}
                        onSelect={() => handleSelect(conv)}
                        onDelete={(e) => handleDelete(conv.id, e)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function groupByDate(
  conversations: Conversation[]
): { label: string; items: Conversation[] }[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: "今日", items: [] },
    { label: "昨日", items: [] },
    { label: "過去7日間", items: [] },
    { label: "それ以前", items: [] },
  ];

  for (const conv of conversations) {
    const d = new Date(conv.updated_at || conv.created_at);
    if (d >= today) groups[0].items.push(conv);
    else if (d >= yesterday) groups[1].items.push(conv);
    else if (d >= weekAgo) groups[2].items.push(conv);
    else groups[3].items.push(conv);
  }

  return groups.filter((g) => g.items.length > 0);
}
