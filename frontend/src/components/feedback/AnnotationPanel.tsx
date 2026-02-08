"use client";

/**
 * AnnotationPanel — Sidebar showing all annotations synced with inline highlights.
 *
 * Design: Editorial review panel. Grouped by message, severity-coded cards,
 * bidirectional sync with mark.js highlights via activeAnnotationId.
 */

import { useRef, useEffect, useCallback, useMemo } from "react";
import {
  X,
  ThumbsUp,
  ThumbsDown,
  MessageSquareQuote,
  Pencil,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type {
  MessageAnnotation,
  MessageFeedback,
  TextSpanSelector,
  AnnotationSeverity,
} from "@/lib/feedback/types";
import type { Message } from "@/lib/marketing/types";

// ---------------------------------------------------------------------------
// Design tokens
// ---------------------------------------------------------------------------

const SEV = {
  critical: { label: "重大", border: "border-l-red-500", bg: "bg-red-50/60", pill: "bg-red-100 text-red-700", dot: "bg-red-500" },
  major:    { label: "中程度", border: "border-l-orange-500", bg: "bg-orange-50/60", pill: "bg-orange-100 text-orange-700", dot: "bg-orange-500" },
  minor:    { label: "軽微", border: "border-l-amber-400", bg: "bg-amber-50/60", pill: "bg-amber-100 text-amber-700", dot: "bg-amber-400" },
  info:     { label: "情報", border: "border-l-blue-500", bg: "bg-blue-50/60", pill: "bg-blue-100 text-blue-700", dot: "bg-blue-500" },
  positive: { label: "良い点", border: "border-l-emerald-500", bg: "bg-emerald-50/60", pill: "bg-emerald-100 text-emerald-700", dot: "bg-emerald-500" },
} satisfies Record<AnnotationSeverity, { label: string; border: string; bg: string; pill: string; dot: string }>;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AnnotationPanelProps {
  messages: Message[];
  feedbackByMessage: Record<string, MessageFeedback>;
  annotationsByMessage: Record<string, MessageAnnotation[]>;
  activeAnnotationId: string | null;
  onSelectAnnotation: (annotationId: string, messageId: string) => void;
  onDeleteAnnotation?: (annotationId: string, messageId: string) => Promise<void>;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AnnotationPanel({
  messages,
  feedbackByMessage,
  annotationsByMessage,
  activeAnnotationId,
  onSelectAnnotation,
  onDeleteAnnotation,
  onClose,
}: AnnotationPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Messages with annotations or feedback
  const groups = useMemo(() => {
    return messages
      .filter(m => m.role === "assistant")
      .map(m => ({
        message: m,
        feedback: feedbackByMessage[m.id] ?? null,
        annotations: annotationsByMessage[m.id] ?? [],
      }))
      .filter(g => g.feedback?.rating || g.annotations.length > 0);
  }, [messages, feedbackByMessage, annotationsByMessage]);

  const totalAnnotations = useMemo(
    () => groups.reduce((n, g) => n + g.annotations.length, 0),
    [groups],
  );

  // Auto-scroll sidebar to active annotation
  useEffect(() => {
    if (!activeAnnotationId || !scrollRef.current) return;
    const el = scrollRef.current.querySelector(`[data-ann-card="${activeAnnotationId}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeAnnotationId]);

  const handleClick = useCallback(
    (id: string, msgId: string) => onSelectAnnotation(id, msgId),
    [onSelectAnnotation],
  );

  // ─── Render ───
  return (
    <div className="w-[300px] shrink-0 flex flex-col h-full border-l border-border/60 bg-gradient-to-b from-white to-slate-50/80">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 flex items-center justify-between border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-[var(--brand-100)]/60 flex items-center justify-center">
            <Pencil className="w-3 h-3 text-[var(--brand-400)]" />
          </div>
          <div>
            <h3 className="text-[13px] font-semibold leading-tight tracking-tight">レビュー</h3>
            <p className="text-[10px] text-muted-foreground leading-tight mt-0.5">
              {totalAnnotations > 0 ? `${totalAnnotations}件のアノテーション` : "テキストを選択して追加"}
            </p>
          </div>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground" onClick={onClose}>
          <X className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* Body */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto annotation-sidebar">
        {groups.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center h-full px-6 py-12">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-4">
              <MessageSquareQuote className="w-5 h-5 text-slate-300" />
            </div>
            <p className="text-[13px] text-muted-foreground text-center leading-relaxed">
              テキストを選択して<br />アノテーションを追加できます
            </p>
          </div>
        ) : (
          <div className="py-2">
            {groups.map((g, gi) => (
              <div key={g.message.id}>
                {/* Message group header */}
                <div className="px-4 pt-3 pb-1.5 flex items-center gap-2">
                  <span className="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-widest">
                    応答 {gi + 1}
                  </span>
                  <div className="flex-1 h-px bg-border/40" />
                  <span className="text-[10px] text-muted-foreground/40">
                    {g.annotations.length}件
                  </span>
                </div>

                {/* Message-level feedback */}
                {g.feedback?.rating && (
                  <div className="mx-3 mb-1.5 rounded-lg bg-white border border-border/40 px-3 py-2.5 flex items-start gap-2.5">
                    <div className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                      g.feedback.rating === "good"
                        ? "bg-emerald-100 text-emerald-600"
                        : "bg-red-100 text-red-500"
                    }`}>
                      {g.feedback.rating === "good"
                        ? <ThumbsUp className="w-2.5 h-2.5" />
                        : <ThumbsDown className="w-2.5 h-2.5" />
                      }
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[11px] font-medium leading-tight">
                        {g.feedback.rating === "good" ? "Good" : "Bad"}
                      </div>
                      {g.feedback.comment && (
                        <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed line-clamp-3">
                          {g.feedback.comment}
                        </p>
                      )}
                      {g.feedback.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {g.feedback.tags.map(t => (
                            <span key={t} className="inline-flex text-[9px] font-medium bg-slate-100 text-slate-500 rounded px-1.5 py-0.5">
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Annotation cards */}
                <div className="px-3 space-y-1.5 pb-2">
                  {g.annotations.map(ann => {
                    const sev = SEV[ann.severity];
                    const sel = ann.selector as TextSpanSelector;
                    const isActive = activeAnnotationId === ann.id;

                    return (
                      <div
                        key={ann.id}
                        role="button"
                        tabIndex={0}
                        data-ann-card={ann.id}
                        onClick={() => handleClick(ann.id, ann.message_id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            handleClick(ann.id, ann.message_id);
                          }
                        }}
                        className={`
                          group/card w-full text-left rounded-lg border-l-[3px] ${sev.border}
                          px-3 py-2.5 transition-all duration-200 cursor-pointer
                          ${isActive
                            ? `${sev.bg} shadow-sm ring-1 ring-[var(--brand-200)]/50`
                            : "bg-white hover:bg-slate-50/80 hover:shadow-sm"
                          }
                        `}
                      >
                        {/* Top row: severity pill + delete */}
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-1.5">
                            <span className={`inline-flex text-[10px] font-semibold rounded px-1.5 py-0.5 leading-none ${sev.pill}`}>
                              {sev.label}
                            </span>
                            {ann.tags.slice(0, 2).map(t => (
                              <span key={t} className="text-[9px] font-medium text-muted-foreground bg-slate-100 rounded px-1.5 py-0.5 leading-none">
                                {t}
                              </span>
                            ))}
                            {ann.tags.length > 2 && (
                              <span className="text-[9px] text-muted-foreground/50">+{ann.tags.length - 2}</span>
                            )}
                          </div>
                          {onDeleteAnnotation && (
                            <button
                              type="button"
                              onClick={async (e) => {
                                e.stopPropagation();
                                await onDeleteAnnotation(ann.id, ann.message_id);
                              }}
                              className="opacity-0 group-hover/card:opacity-100 transition-opacity p-0.5 rounded hover:bg-red-50 text-slate-300 hover:text-red-400"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          )}
                        </div>

                        {/* Quote */}
                        {sel.quote?.exact && (
                          <p className="text-[11px] text-slate-500 leading-relaxed line-clamp-2 pl-2 border-l border-slate-200">
                            {sel.quote.exact.slice(0, 80)}{sel.quote.exact.length > 80 ? "..." : ""}
                          </p>
                        )}

                        {/* Comment */}
                        {ann.comment && (
                          <p className="text-[11px] text-slate-700 leading-relaxed mt-1.5 line-clamp-2">
                            {ann.comment}
                          </p>
                        )}

                        {/* Correction */}
                        {ann.correction && (
                          <div className="mt-1.5 text-[10px] text-emerald-700 bg-emerald-50/80 rounded px-2 py-1 border border-emerald-100 line-clamp-1">
                            <span className="font-medium">修正:</span> {ann.correction}
                          </div>
                        )}

                        {/* Timestamp */}
                        <div className="text-[9px] text-slate-300 mt-2">
                          {new Date(ann.created_at).toLocaleString("ja-JP", {
                            month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
