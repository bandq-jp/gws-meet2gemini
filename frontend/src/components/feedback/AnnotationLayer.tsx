"use client";

/**
 * AnnotationLayer - Text selection annotation overlay for FB mode.
 *
 * When FB mode is active, this wraps assistant message content and:
 * 1. Listens for text selection events
 * 2. Shows a popover to create annotations on selected text
 * 3. Renders existing annotations as highlights
 */

import { useRef, useState, useCallback, useEffect } from "react";
import { MessageSquarePlus, X, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { TagSelector } from "./TagSelector";
import { captureTextSelection, resolveSelector, simpleHash } from "@/lib/feedback/text-selector";
import type {
  FeedbackTag,
  MessageAnnotation,
  AnnotationCreatePayload,
  TextSpanSelector,
  AnnotationSeverity,
} from "@/lib/feedback/types";

interface AnnotationLayerProps {
  messageId: string;
  conversationId: string;
  plainText: string;
  annotations: MessageAnnotation[];
  tags: FeedbackTag[];
  onCreateAnnotation: (payload: AnnotationCreatePayload) => Promise<unknown>;
  onDeleteAnnotation: (annotationId: string, messageId: string) => Promise<void>;
  children: React.ReactNode;
}

const SEVERITY_OPTIONS: { value: AnnotationSeverity; label: string; color: string }[] = [
  { value: "critical", label: "重大", color: "#ef4444" },
  { value: "major", label: "中程度", color: "#f97316" },
  { value: "minor", label: "軽微", color: "#eab308" },
  { value: "info", label: "情報", color: "#6b7280" },
  { value: "positive", label: "良い", color: "#22c55e" },
];

export function AnnotationLayer({
  messageId,
  conversationId,
  plainText,
  annotations,
  tags,
  onCreateAnnotation,
  onDeleteAnnotation,
  children,
}: AnnotationLayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pendingSelector, setPendingSelector] = useState<TextSpanSelector | null>(null);
  const [popoverPos, setPopoverPos] = useState<{ x: number; y: number } | null>(null);
  const [comment, setComment] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [severity, setSeverity] = useState<AnnotationSeverity>("info");
  const [correction, setCorrection] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [viewingAnnotation, setViewingAnnotation] = useState<MessageAnnotation | null>(null);

  // Listen for mouseup to detect text selection
  const handleMouseUp = useCallback(() => {
    if (!containerRef.current) return;
    // Small delay to let selection finalize
    setTimeout(() => {
      if (!containerRef.current) return;
      const selector = captureTextSelection(containerRef.current);
      if (selector && selector.quote.exact.length > 2) {
        const selection = window.getSelection();
        if (selection && selection.rangeCount > 0) {
          const range = selection.getRangeAt(0);
          const rect = range.getBoundingClientRect();
          const containerRect = containerRef.current.getBoundingClientRect();
          setPopoverPos({
            x: rect.left - containerRect.left + rect.width / 2,
            y: rect.top - containerRect.top - 8,
          });
        }
        setPendingSelector(selector);
      }
    }, 10);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!pendingSelector) return;
    setSubmitting(true);
    try {
      await onCreateAnnotation({
        message_id: messageId,
        conversation_id: conversationId,
        selector: pendingSelector,
        comment: comment || null,
        tags: selectedTags.length > 0 ? selectedTags : null,
        severity,
        correction: correction || null,
        content_hash: simpleHash(plainText),
      });
      // Reset
      setPendingSelector(null);
      setPopoverPos(null);
      setComment("");
      setSelectedTags([]);
      setSeverity("info");
      setCorrection("");
      window.getSelection()?.removeAllRanges();
    } finally {
      setSubmitting(false);
    }
  }, [pendingSelector, messageId, conversationId, comment, selectedTags, severity, correction, plainText, onCreateAnnotation]);

  const cancelAnnotation = useCallback(() => {
    setPendingSelector(null);
    setPopoverPos(null);
    setComment("");
    setSelectedTags([]);
    setCorrection("");
    window.getSelection()?.removeAllRanges();
  }, []);

  // Resolve existing annotations to highlight ranges
  const textAnnotations = annotations.filter(
    a => (a.selector as TextSpanSelector).type === "text_span"
  );

  const severityColor = (sev: AnnotationSeverity) => {
    switch (sev) {
      case "critical": return "bg-red-100 border-red-300";
      case "major": return "bg-orange-100 border-orange-300";
      case "minor": return "bg-yellow-100 border-yellow-300";
      case "positive": return "bg-emerald-100 border-emerald-300";
      default: return "bg-blue-100 border-blue-300";
    }
  };

  return (
    <div className="relative" ref={containerRef} onMouseUp={handleMouseUp}>
      {/* Render children (message content) */}
      {children}

      {/* Existing annotation badges */}
      {textAnnotations.length > 0 && (
        <div className="mt-2 space-y-1">
          {textAnnotations.map(ann => {
            const sel = ann.selector as TextSpanSelector;
            return (
              <div
                key={ann.id}
                className={`flex items-start gap-2 rounded-md border px-2 py-1.5 text-xs cursor-pointer transition-colors hover:shadow-sm ${severityColor(ann.severity)}`}
                onClick={() => setViewingAnnotation(ann)}
              >
                <span className="font-medium text-muted-foreground shrink-0">
                  &ldquo;{sel.quote.exact.slice(0, 40)}{sel.quote.exact.length > 40 ? "..." : ""}&rdquo;
                </span>
                {ann.comment && (
                  <span className="text-foreground truncate">{ann.comment}</span>
                )}
                <div className="ml-auto flex gap-1 shrink-0">
                  {ann.tags?.map(t => (
                    <span key={t} className="rounded-full bg-white/60 px-1.5 py-0.5 text-[10px]">{t}</span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* New annotation popover (appears at selection position) */}
      {pendingSelector && popoverPos && (
        <div
          className="absolute z-50"
          style={{ left: popoverPos.x - 160, top: popoverPos.y - 4, transform: "translateY(-100%)" }}
        >
          <div className="bg-white rounded-lg shadow-xl border p-3 w-80 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-sm font-medium">
                <MessageSquarePlus className="w-4 h-4" />
                アノテーション
              </div>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={cancelAnnotation}>
                <X className="w-3.5 h-3.5" />
              </Button>
            </div>

            <div className="bg-muted rounded px-2 py-1 text-xs text-muted-foreground italic">
              &ldquo;{pendingSelector.quote.exact.slice(0, 80)}{pendingSelector.quote.exact.length > 80 ? "..." : ""}&rdquo;
            </div>

            {/* Severity */}
            <div className="flex gap-1">
              {SEVERITY_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setSeverity(opt.value)}
                  className={`rounded-full px-2 py-0.5 text-[11px] font-medium transition-all ${
                    severity === opt.value
                      ? "ring-2 ring-offset-1 shadow-sm text-white"
                      : "opacity-60 hover:opacity-100"
                  }`}
                  style={{
                    backgroundColor: severity === opt.value ? opt.color : `${opt.color}20`,
                    color: severity === opt.value ? "white" : opt.color,
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Tags */}
            <TagSelector
              tags={tags}
              selected={selectedTags}
              onChange={setSelectedTags}
            />

            <Textarea
              placeholder="コメント"
              value={comment}
              onChange={e => setComment(e.target.value)}
              className="text-sm min-h-[50px] resize-none"
              autoFocus
            />

            <Textarea
              placeholder="修正案（任意）"
              value={correction}
              onChange={e => setCorrection(e.target.value)}
              className="text-sm min-h-[40px] resize-none"
            />

            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={cancelAnnotation}>キャンセル</Button>
              <Button size="sm" onClick={handleSubmit} disabled={submitting}>
                {submitting ? "保存中..." : "保存"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Viewing annotation detail */}
      {viewingAnnotation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={() => setViewingAnnotation(null)}>
          <div className="bg-white rounded-lg shadow-xl border p-4 w-96 space-y-3" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">アノテーション詳細</h4>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-red-500 hover:text-red-700"
                  onClick={async () => {
                    await onDeleteAnnotation(viewingAnnotation.id, messageId);
                    setViewingAnnotation(null);
                  }}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setViewingAnnotation(null)}>
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
            <div className="bg-muted rounded px-2 py-1 text-xs italic">
              &ldquo;{(viewingAnnotation.selector as TextSpanSelector).quote?.exact || "N/A"}&rdquo;
            </div>
            <div className="text-xs space-y-1">
              <div><span className="font-medium">深刻度:</span> {viewingAnnotation.severity}</div>
              {viewingAnnotation.tags.length > 0 && (
                <div><span className="font-medium">タグ:</span> {viewingAnnotation.tags.join(", ")}</div>
              )}
              {viewingAnnotation.comment && (
                <div><span className="font-medium">コメント:</span> {viewingAnnotation.comment}</div>
              )}
              {viewingAnnotation.correction && (
                <div><span className="font-medium">修正案:</span> {viewingAnnotation.correction}</div>
              )}
              <div className="text-muted-foreground">{viewingAnnotation.user_email} - {new Date(viewingAnnotation.created_at).toLocaleString("ja-JP")}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
