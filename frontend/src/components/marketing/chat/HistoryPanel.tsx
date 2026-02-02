"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  MessageSquare,
  Plus,
  Trash2,
  Pencil,
  Check,
  X,
} from "lucide-react";
import type { Conversation } from "@/lib/marketing-types";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  ensureClientSecret: () => Promise<string>;
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "今日";
  if (diffDays === 1) return "昨日";
  if (diffDays < 7) return `${diffDays}日前`;
  return d.toLocaleDateString("ja-JP", { month: "short", day: "numeric" });
}

function groupByDate(conversations: Conversation[]) {
  const groups: { label: string; items: Conversation[] }[] = [];
  const labelMap = new Map<string, Conversation[]>();

  for (const conv of conversations) {
    const label = formatDate(conv.created_at);
    if (!labelMap.has(label)) {
      labelMap.set(label, []);
    }
    labelMap.get(label)!.push(conv);
  }

  for (const [label, items] of labelMap) {
    groups.push({ label, items });
  }
  return groups;
}

export function HistoryPanel({
  open,
  onOpenChange,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  ensureClientSecret,
}: Props) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const loadConversations = useCallback(async () => {
    setLoading(true);
    try {
      const token = await ensureClientSecret();
      const res = await fetch("/api/marketing/chat/threads", {
        headers: { "x-marketing-client-secret": token },
      });
      if (res.ok) {
        const data = await res.json();
        setConversations(data.threads || []);
      }
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoading(false);
    }
  }, [ensureClientSecret]);

  useEffect(() => {
    if (open) {
      loadConversations();
    }
  }, [open, loadConversations]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("この会話を削除しますか？")) return;
    try {
      const token = await ensureClientSecret();
      await fetch(`/api/marketing/chat/threads/${id}`, {
        method: "DELETE",
        headers: { "x-marketing-client-secret": token },
      });
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const handleRenameStart = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleRenameSubmit = async (id: string) => {
    const trimmed = editTitle.trim();
    if (!trimmed) {
      setEditingId(null);
      return;
    }
    try {
      const token = await ensureClientSecret();
      await fetch(`/api/marketing/chat/threads/${id}/title`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "x-marketing-client-secret": token,
        },
        body: JSON.stringify({ title: trimmed }),
      });
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: trimmed } : c))
      );
    } catch (err) {
      console.error("Failed to rename:", err);
    } finally {
      setEditingId(null);
    }
  };

  const handleRenameCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  const groups = groupByDate(conversations);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-[320px] sm:w-[360px] p-0">
        <SheetHeader className="px-4 pt-4 pb-3 border-b border-[#e5e7eb]">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-sm font-bold">会話履歴</SheetTitle>
            <button
              onClick={() => {
                onNewConversation();
                onOpenChange(false);
              }}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-white bg-[var(--brand-400)] hover:bg-[#176d80] rounded-lg transition-colors cursor-pointer"
            >
              <Plus className="w-3 h-3" />
              新規
            </button>
          </div>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-64px)]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-5 h-5 border-2 border-[var(--brand-400)] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-12 text-sm text-[#9ca3af]">
              会話履歴がありません
            </div>
          ) : (
            <div className="px-2 py-2">
              {groups.map((group) => (
                <div key={group.label} className="mb-3">
                  <div className="px-2 py-1 text-[10px] font-medium text-[#9ca3af] uppercase tracking-wider">
                    {group.label}
                  </div>
                  {group.items.map((conv) => {
                    const isActive = conv.id === currentConversationId;
                    const isEditing = editingId === conv.id;

                    return (
                      <div
                        key={conv.id}
                        onClick={() => {
                          if (!isEditing) {
                            onSelectConversation(conv.id);
                            onOpenChange(false);
                          }
                        }}
                        className={`group flex items-center gap-2 px-2.5 py-2 rounded-lg mb-0.5 cursor-pointer transition-colors ${
                          isActive
                            ? "bg-[var(--brand-400)]/10 text-[var(--brand-400)]"
                            : "hover:bg-[#f0f1f5] text-[#374151]"
                        }`}
                      >
                        <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-50" />
                        {isEditing ? (
                          <div className="flex-1 flex items-center gap-1 min-w-0">
                            <input
                              value={editTitle}
                              onChange={(e) => setEditTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter")
                                  handleRenameSubmit(conv.id);
                                if (e.key === "Escape") setEditingId(null);
                              }}
                              onClick={(e) => e.stopPropagation()}
                              className="flex-1 min-w-0 px-1.5 py-0.5 text-xs border border-[#e5e7eb] rounded focus:outline-none focus:border-[var(--brand-400)]"
                              autoFocus
                            />
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRenameSubmit(conv.id);
                              }}
                              className="p-0.5 hover:text-[#10b981] cursor-pointer"
                            >
                              <Check className="w-3 h-3" />
                            </button>
                            <button
                              onClick={handleRenameCancel}
                              className="p-0.5 hover:text-red-500 cursor-pointer"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ) : (
                          <>
                            <span className="flex-1 text-xs truncate min-w-0">
                              {conv.title || "新しい会話"}
                            </span>
                            <div className="hidden group-hover:flex items-center gap-0.5 shrink-0">
                              <button
                                onClick={(e) => handleRenameStart(conv, e)}
                                className="p-1 hover:text-[var(--brand-400)] rounded transition-colors cursor-pointer"
                              >
                                <Pencil className="w-3 h-3" />
                              </button>
                              <button
                                onClick={(e) => handleDelete(conv.id, e)}
                                className="p-1 hover:text-red-500 rounded transition-colors cursor-pointer"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
