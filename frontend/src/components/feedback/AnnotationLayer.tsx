"use client";

/**
 * AnnotationLayer - Inline text annotation for FB mode.
 *
 * Architecture:
 * - contentRef wraps ONLY the message content (no UI elements inside)
 * - mark.js applies <mark> highlights to the content DOM
 * - UI overlays (form, popover) use createPortal to document.body
 *
 * Flow: text selection → full annotation form opens directly (no intermediate toolbar)
 */

import { useRef, useState, useCallback, useLayoutEffect, useEffect } from "react";
import { createPortal } from "react-dom";
import Mark from "mark.js";
import { X, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { TagSelector } from "./TagSelector";
import { captureTextSelection, resolveSelector, simpleHash } from "@/lib/feedback/text-selector";
import type {
  FeedbackTag,
  MessageAnnotation,
  AnnotationCreatePayload,
  TextSpanSelector,
  AnnotationSeverity,
} from "@/lib/feedback/types";

// ---------------------------------------------------------------------------
// Types & Constants
// ---------------------------------------------------------------------------

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

const SEVERITY_OPTIONS: { value: AnnotationSeverity; label: string }[] = [
  { value: "critical", label: "重大" },
  { value: "major", label: "中" },
  { value: "minor", label: "軽" },
  { value: "info", label: "情報" },
  { value: "positive", label: "良" },
];

const SEVERITY_BADGE: Record<AnnotationSeverity, string> = {
  critical: "text-red-700 bg-red-50 border-red-200",
  major: "text-orange-700 bg-orange-50 border-orange-200",
  minor: "text-yellow-700 bg-yellow-50 border-yellow-200",
  info: "text-blue-700 bg-blue-50 border-blue-200",
  positive: "text-emerald-700 bg-emerald-50 border-emerald-200",
};

const SEVERITY_LABEL: Record<AnnotationSeverity, string> = {
  critical: "重大",
  major: "中程度",
  minor: "軽微",
  info: "情報",
  positive: "良い点",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

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
  const contentRef = useRef<HTMLDivElement>(null);
  const markRef = useRef<Mark | null>(null);

  // --- Annotation Form (opens directly on text selection) ---
  const [form, setForm] = useState<{
    rect: DOMRect;
    selector: TextSpanSelector;
    severity: AnnotationSeverity;
  } | null>(null);
  const [formComment, setFormComment] = useState("");
  const [formTags, setFormTags] = useState<string[]>([]);
  const [formCorrection, setFormCorrection] = useState("");
  const [formSubmitting, setFormSubmitting] = useState(false);

  // --- Highlight Detail Popover ---
  const [detail, setDetail] = useState<{
    annotation: MessageAnnotation;
    rect: DOMRect;
  } | null>(null);

  // Filter text_span annotations
  const textAnnotations = annotations.filter(
    a => (a.selector as TextSpanSelector).type === "text_span"
  );

  // =========================================================================
  // mark.js: Apply inline highlights
  // =========================================================================
  useLayoutEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    if (markRef.current) {
      markRef.current.unmark();
    }
    markRef.current = new Mark(el);

    if (textAnnotations.length === 0) return;

    const rangeMap = new Map<object, { id: string; severity: AnnotationSeverity }>();
    const ranges: { start: number; length: number }[] = [];

    for (const ann of textAnnotations) {
      const sel = ann.selector as TextSpanSelector;
      const resolved = resolveSelector(plainText, sel);
      if (!resolved) continue;
      const range = { start: resolved.start, length: resolved.end - resolved.start };
      rangeMap.set(range, { id: ann.id, severity: ann.severity });
      ranges.push(range);
    }

    if (ranges.length === 0) return;

    markRef.current.markRanges(ranges, {
      each: (element, range) => {
        const info = rangeMap.get(range);
        if (!info) return;
        element.classList.add("annotation-hl", `annotation-hl-${info.severity}`);
        element.dataset.annotationId = info.id;
        element.addEventListener("click", (e) => {
          e.stopPropagation();
          const ann = textAnnotations.find(a => a.id === info.id);
          if (ann) {
            setDetail({
              annotation: ann,
              rect: (e.target as HTMLElement).getBoundingClientRect(),
            });
            setForm(null);
          }
        });
      },
    });

    return () => {
      markRef.current?.unmark();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textAnnotations.length, plainText]);

  // =========================================================================
  // Text selection → directly open form
  // =========================================================================
  const handleMouseUp = useCallback(() => {
    const el = contentRef.current;
    if (!el) return;
    if (form) return; // Don't capture while form is open

    requestAnimationFrame(() => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
        return;
      }

      if (!el.contains(selection.anchorNode) || !el.contains(selection.focusNode)) {
        return;
      }

      const selector = captureTextSelection(el);
      if (selector && selector.quote.exact.trim().length > 2) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        setForm({ rect, selector, severity: "info" });
        setFormComment("");
        setFormTags([]);
        setFormCorrection("");
        setDetail(null);
        // Clear selection after capturing
        selection.removeAllRanges();
      }
    });
  }, [form]);

  // Dismiss overlays on click outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest("[data-annotation-overlay]")) return;
      if (target.closest("mark.annotation-hl")) return;
      setDetail(null);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Dismiss on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setForm(null);
        setDetail(null);
        window.getSelection()?.removeAllRanges();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  // =========================================================================
  // Submit annotation
  // =========================================================================
  const handleFormSubmit = useCallback(async () => {
    if (!form) return;
    setFormSubmitting(true);
    try {
      await onCreateAnnotation({
        message_id: messageId,
        conversation_id: conversationId,
        selector: form.selector,
        severity: form.severity,
        comment: formComment || null,
        tags: formTags.length > 0 ? formTags : null,
        correction: formCorrection || null,
        content_hash: simpleHash(plainText),
      });
      setForm(null);
    } finally {
      setFormSubmitting(false);
    }
  }, [form, messageId, conversationId, formComment, formTags, formCorrection, plainText, onCreateAnnotation]);

  // =========================================================================
  // Render
  // =========================================================================
  return (
    <div className="relative">
      {/* Content area — ONLY message content, no UI elements */}
      <div
        ref={contentRef}
        onMouseUp={handleMouseUp}
        className="annotation-content-area"
        style={{ userSelect: "text" }}
      >
        {children}
      </div>

      {/* ===== Annotation Form (Portal — opens directly on text selection) ===== */}
      {form && typeof document !== "undefined" && (() => {
        const gap = 8;
        const formW = 336;
        const spaceAbove = form.rect.top;
        const spaceBelow = window.innerHeight - form.rect.bottom;
        const placeBelow = spaceBelow >= 280 || spaceBelow > spaceAbove;
        const top = placeBelow
          ? Math.min(form.rect.bottom + gap, window.innerHeight - 40)
          : Math.max(gap, form.rect.top - gap);
        const left = Math.max(12, Math.min(
          form.rect.left + form.rect.width / 2 - formW / 2,
          window.innerWidth - formW - 12,
        ));
        const maxH = placeBelow
          ? window.innerHeight - form.rect.bottom - gap * 2
          : form.rect.top - gap * 2;

        return createPortal(
          <div
            data-annotation-overlay
            className={`fixed z-[9999] animate-in fade-in duration-150 ${
              placeBelow ? "slide-in-from-top-1" : "slide-in-from-bottom-1"
            }`}
            style={{
              left,
              top,
              ...(!placeBelow && { transform: "translateY(-100%)" }),
            }}
          >
            <div
              className="bg-white rounded-xl shadow-2xl border border-border/60 overflow-hidden"
              style={{ width: formW, maxHeight: Math.max(maxH, 200) }}
            >
              <div className="overflow-y-auto overscroll-contain" style={{ maxHeight: Math.max(maxH - 2, 198) }}>
                <div className="p-3.5 space-y-3">
                  {/* Header */}
                  <div className="flex items-center justify-between sticky top-0 bg-white z-10 -mt-3.5 -mx-3.5 px-3.5 pt-3.5 pb-2 border-b border-border/30">
                    <span className="text-sm font-semibold">アノテーション</span>
                    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setForm(null)}>
                      <X className="w-3.5 h-3.5" />
                    </Button>
                  </div>

                  {/* Quote */}
                  <div className="bg-muted/50 rounded-lg px-3 py-2 text-xs text-muted-foreground leading-relaxed border-l-2 border-[var(--brand-300)]">
                    &ldquo;{form.selector.quote.exact.slice(0, 120)}
                    {form.selector.quote.exact.length > 120 ? "..." : ""}&rdquo;
                  </div>

                  {/* Severity */}
                  <div>
                    <label className="text-[11px] font-medium text-muted-foreground mb-1.5 block">重大さ</label>
                    <div className="flex gap-1.5 flex-wrap">
                      {SEVERITY_OPTIONS.map(opt => (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => setForm(f => f ? { ...f, severity: opt.value } : null)}
                          className={`rounded-full px-3 py-1 text-[11px] font-medium transition-all border ${
                            form.severity === opt.value
                              ? `${SEVERITY_BADGE[opt.value]} border-current shadow-sm`
                              : "bg-white text-muted-foreground border-border hover:border-foreground/30"
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Tags */}
                  {tags.length > 0 && (
                    <div>
                      <label className="text-[11px] font-medium text-muted-foreground mb-1.5 block">タグ</label>
                      <TagSelector tags={tags} selected={formTags} onChange={setFormTags} />
                    </div>
                  )}

                  {/* Comment */}
                  <Textarea
                    placeholder="コメント（任意）"
                    value={formComment}
                    onChange={e => setFormComment(e.target.value)}
                    className="text-sm min-h-[50px] resize-none"
                    autoFocus
                  />

                  {/* Correction */}
                  <Textarea
                    placeholder="修正案（任意）"
                    value={formCorrection}
                    onChange={e => setFormCorrection(e.target.value)}
                    className="text-sm min-h-[40px] resize-none"
                  />

                  {/* Actions */}
                  <div className="flex justify-end gap-2 pt-1 sticky bottom-0 bg-white -mb-3.5 -mx-3.5 px-3.5 pb-3.5 pt-2 border-t border-border/30">
                    <Button variant="outline" size="sm" onClick={() => setForm(null)}>
                      キャンセル
                    </Button>
                    <Button size="sm" onClick={handleFormSubmit} disabled={formSubmitting}>
                      {formSubmitting ? "保存中..." : "保存"}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>,
          document.body,
        );
      })()}

      {/* ===== Highlight Detail Popover (Portal) ===== */}
      {detail && typeof document !== "undefined" && (() => {
        const gap = 6;
        const popW = 288;
        const spaceBelow = window.innerHeight - detail.rect.bottom;
        const placeBelow = spaceBelow >= 180 || spaceBelow > detail.rect.top;
        const top = placeBelow
          ? detail.rect.bottom + gap
          : Math.max(gap, detail.rect.top - gap);
        const left = Math.max(12, Math.min(
          detail.rect.left + detail.rect.width / 2 - popW / 2,
          window.innerWidth - popW - 12,
        ));

        return createPortal(
          <div
            data-annotation-overlay
            className={`fixed z-[9999] animate-in fade-in zoom-in-95 duration-150`}
            style={{
              left,
              top,
              ...(!placeBelow && { transform: "translateY(-100%)" }),
            }}
          >
            <div className="bg-white rounded-xl shadow-2xl border border-border/60" style={{ width: popW }}>
              <div className="p-3 space-y-2">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <span className={`text-[11px] font-semibold rounded-full px-2.5 py-0.5 border ${SEVERITY_BADGE[detail.annotation.severity]}`}>
                    {SEVERITY_LABEL[detail.annotation.severity]}
                  </span>
                  <div className="flex items-center gap-0.5">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-red-400 hover:text-red-600 hover:bg-red-50"
                      onClick={async () => {
                        await onDeleteAnnotation(detail.annotation.id, messageId);
                        setDetail(null);
                      }}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setDetail(null)}>
                      <X className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>

                {/* Quote */}
                <div className="text-xs text-muted-foreground italic leading-relaxed">
                  &ldquo;{(detail.annotation.selector as TextSpanSelector).quote?.exact.slice(0, 80)}
                  {((detail.annotation.selector as TextSpanSelector).quote?.exact.length || 0) > 80 ? "..." : ""}&rdquo;
                </div>

                {/* Tags */}
                {detail.annotation.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {detail.annotation.tags.map(t => (
                      <span key={t} className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                        {t}
                      </span>
                    ))}
                  </div>
                )}

                {/* Comment */}
                {detail.annotation.comment && (
                  <p className="text-xs text-foreground leading-relaxed">{detail.annotation.comment}</p>
                )}

                {/* Correction */}
                {detail.annotation.correction && (
                  <div className="text-xs bg-emerald-50 rounded-md px-2 py-1.5 border border-emerald-200">
                    <span className="font-medium text-emerald-700">修正案: </span>
                    <span className="text-emerald-900">{detail.annotation.correction}</span>
                  </div>
                )}

                {/* Meta */}
                <div className="text-[10px] text-muted-foreground/60 pt-1.5 border-t border-border/40">
                  {new Date(detail.annotation.created_at).toLocaleString("ja-JP")}
                </div>
              </div>
            </div>
          </div>,
          document.body,
        );
      })()}
    </div>
  );
}
