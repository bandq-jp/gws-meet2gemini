"use client";

/**
 * FeedbackBar - Compact feedback controls below each assistant message.
 *
 * - Thumbs up/down are toggleable (click again to un-select)
 * - Good click submits immediately but does NOT lock the UI
 * - "コメント" button always visible to add/edit tags, comment, correction
 * - Existing feedback is pre-filled and editable
 */

import { useState, useCallback, useEffect } from "react";
import { ThumbsUp, ThumbsDown, MessageSquarePlus, X, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import { TagSelector } from "./TagSelector";
import type {
  FeedbackTag,
  FeedbackCreatePayload,
  MessageFeedback,
  Rating,
} from "@/lib/feedback/types";

interface FeedbackBarProps {
  messageId: string;
  existingFeedback?: MessageFeedback | null;
  tags: FeedbackTag[];
  onSubmit: (messageId: string, payload: FeedbackCreatePayload) => Promise<unknown>;
  isFeedbackMode?: boolean;
}

export function FeedbackBar({
  messageId,
  existingFeedback,
  tags,
  onSubmit,
  isFeedbackMode,
}: FeedbackBarProps) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [selectedRating, setSelectedRating] = useState<Rating | null>(
    existingFeedback?.rating || null
  );
  const [comment, setComment] = useState(existingFeedback?.comment || "");
  const [correction, setCorrection] = useState(existingFeedback?.correction || "");
  const [selectedTags, setSelectedTags] = useState<string[]>(existingFeedback?.tags || []);
  const [submitting, setSubmitting] = useState(false);

  // Sync when existingFeedback changes (e.g., loaded from server)
  useEffect(() => {
    setSelectedRating(existingFeedback?.rating || null);
    setComment(existingFeedback?.comment || "");
    setCorrection(existingFeedback?.correction || "");
    setSelectedTags(existingFeedback?.tags || []);
  }, [existingFeedback]);

  const hasExisting = !!existingFeedback?.rating;
  const hasDetails = !!(existingFeedback?.comment || existingFeedback?.tags?.length);

  // Guard: check if message has been persisted (UUID format)
  const isPersistedMessage = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(messageId);

  // Toggle rating: click same thumb to un-select, different thumb to switch
  const handleToggleRating = useCallback(async (rating: Rating) => {
    if (!isPersistedMessage) return;
    const newRating = selectedRating === rating ? null : rating;
    setSelectedRating(newRating);
    setSubmitting(true);
    try {
      await onSubmit(messageId, {
        rating: newRating,
        comment: comment || null,
        tags: selectedTags.length > 0 ? selectedTags : null,
        correction: correction || null,
      });
    } finally {
      setSubmitting(false);
    }
  }, [messageId, onSubmit, isPersistedMessage, selectedRating, comment, selectedTags, correction]);

  // Submit detailed feedback from popover
  const handleSubmitDetailed = useCallback(async () => {
    if (!isPersistedMessage) return;
    setSubmitting(true);
    try {
      await onSubmit(messageId, {
        rating: selectedRating,
        comment: comment || null,
        correction: correction || null,
        tags: selectedTags.length > 0 ? selectedTags : null,
      });
      setPopoverOpen(false);
    } finally {
      setSubmitting(false);
    }
  }, [messageId, isPersistedMessage, selectedRating, comment, correction, selectedTags, onSubmit]);

  // Reset all feedback
  const handleReset = useCallback(async () => {
    if (!isPersistedMessage) return;
    setSubmitting(true);
    try {
      await onSubmit(messageId, {
        rating: null,
        comment: null,
        correction: null,
        tags: null,
      });
      setSelectedRating(null);
      setComment("");
      setCorrection("");
      setSelectedTags([]);
      setPopoverOpen(false);
    } finally {
      setSubmitting(false);
    }
  }, [messageId, onSubmit]);

  return (
    <div
      className="flex items-center gap-1 mt-1.5 opacity-0 group-hover/msg:opacity-100 transition-opacity duration-200"
      style={isFeedbackMode ? { opacity: 1 } : undefined}
    >
      {/* Thumbs Up - toggleable */}
      <Button
        variant="ghost"
        size="icon"
        className={`h-7 w-7 rounded-full transition-colors ${
          selectedRating === "good"
            ? "bg-emerald-100 text-emerald-600 hover:bg-emerald-200"
            : "text-muted-foreground/60 hover:text-emerald-600 hover:bg-emerald-50"
        }`}
        onClick={() => handleToggleRating("good")}
        disabled={submitting}
      >
        <ThumbsUp className="w-3.5 h-3.5" />
      </Button>

      {/* Thumbs Down - toggleable */}
      <Button
        variant="ghost"
        size="icon"
        className={`h-7 w-7 rounded-full transition-colors ${
          selectedRating === "bad"
            ? "bg-red-100 text-red-600 hover:bg-red-200"
            : "text-muted-foreground/60 hover:text-red-500 hover:bg-red-50"
        }`}
        onClick={() => handleToggleRating("bad")}
        disabled={submitting}
      >
        <ThumbsDown className="w-3.5 h-3.5" />
      </Button>

      {/* Comment / Edit button - always visible */}
      <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className={`h-7 px-2 text-xs transition-colors ${
              hasDetails
                ? "text-blue-600 hover:text-blue-700"
                : "text-muted-foreground/60 hover:text-foreground"
            }`}
          >
            <MessageSquarePlus className="w-3.5 h-3.5 mr-1" />
            {hasDetails ? "編集" : "コメント"}
          </Button>
        </PopoverTrigger>

        <PopoverContent align="start" className="w-80 p-0" sideOffset={8}>
          <div className="p-3 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">フィードバック</h4>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setPopoverOpen(false)}>
                <X className="w-3.5 h-3.5" />
              </Button>
            </div>

            {/* Tags */}
            {tags.length > 0 && (
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">
                  {selectedRating === "good" ? "良かった点" : selectedRating === "bad" ? "問題点" : "タグ"}
                </label>
                <TagSelector
                  tags={tags}
                  selected={selectedTags}
                  onChange={setSelectedTags}
                  sentiment={selectedRating === "good" ? "positive" : selectedRating === "bad" ? "negative" : "all"}
                />
              </div>
            )}

            {/* Comment */}
            <Textarea
              placeholder="コメント（任意）"
              value={comment}
              onChange={e => setComment(e.target.value)}
              className="text-sm min-h-[60px] resize-none"
            />

            {/* Correction */}
            <Textarea
              placeholder="修正案（正しい回答はこうあるべき）"
              value={correction}
              onChange={e => setCorrection(e.target.value)}
              className="text-sm min-h-[50px] resize-none"
            />

            <div className="flex items-center justify-between">
              {/* Reset button */}
              {hasExisting && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-muted-foreground hover:text-red-600"
                  onClick={handleReset}
                  disabled={submitting}
                >
                  <RotateCcw className="w-3 h-3 mr-1" />
                  リセット
                </Button>
              )}
              <div className="flex gap-2 ml-auto">
                <Button variant="outline" size="sm" onClick={() => setPopoverOpen(false)}>
                  キャンセル
                </Button>
                <Button size="sm" onClick={handleSubmitDetailed} disabled={submitting}>
                  {submitting ? "送信中..." : "保存"}
                </Button>
              </div>
            </div>
          </div>
        </PopoverContent>
      </Popover>

      {/* Subtle indicator when feedback exists */}
      {hasExisting && !popoverOpen && (
        <span className={`inline-block w-1.5 h-1.5 rounded-full ml-0.5 ${
          selectedRating === "good" ? "bg-emerald-400" : "bg-red-400"
        }`} />
      )}
    </div>
  );
}
