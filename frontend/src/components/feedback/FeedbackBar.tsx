"use client";

/**
 * FeedbackBar - Compact feedback controls shown below each assistant message.
 *
 * Normal mode: 👍 👎 + "詳細FB" button
 * Shows a popover for detailed feedback when 👎 is clicked or "詳細FB" is triggered.
 */

import { useState, useCallback } from "react";
import { ThumbsUp, ThumbsDown, MessageSquarePlus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import { TagSelector } from "./TagSelector";
import { DimensionRating } from "./DimensionRating";
import type {
  FeedbackTag,
  FeedbackDimension,
  FeedbackCreatePayload,
  MessageFeedback,
  Rating,
} from "@/lib/feedback/types";

interface FeedbackBarProps {
  messageId: string;
  existingFeedback?: MessageFeedback | null;
  tags: FeedbackTag[];
  dimensions: FeedbackDimension[];
  onSubmit: (messageId: string, payload: FeedbackCreatePayload) => Promise<unknown>;
  isFeedbackMode?: boolean;
}

export function FeedbackBar({
  messageId,
  existingFeedback,
  tags,
  dimensions,
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
  const [dimensionScores, setDimensionScores] = useState<Record<string, number>>(
    existingFeedback?.dimension_scores || {}
  );
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(!!existingFeedback?.rating);

  const handleQuickRating = useCallback(async (rating: Rating) => {
    setSelectedRating(rating);
    if (rating === "good") {
      setSubmitting(true);
      try {
        await onSubmit(messageId, { rating });
        setSubmitted(true);
      } finally {
        setSubmitting(false);
      }
    } else {
      setPopoverOpen(true);
    }
  }, [messageId, onSubmit]);

  const handleSubmitDetailed = useCallback(async () => {
    setSubmitting(true);
    try {
      const payload: FeedbackCreatePayload = {
        rating: selectedRating,
        comment: comment || null,
        correction: correction || null,
        tags: selectedTags.length > 0 ? selectedTags : null,
        dimension_scores: Object.keys(dimensionScores).length > 0 ? dimensionScores : null,
      };
      await onSubmit(messageId, payload);
      setSubmitted(true);
      setPopoverOpen(false);
    } finally {
      setSubmitting(false);
    }
  }, [messageId, selectedRating, comment, correction, selectedTags, dimensionScores, onSubmit]);

  const currentRating = existingFeedback?.rating || selectedRating;

  return (
    <div className="flex items-center gap-1 mt-2 opacity-0 group-hover/msg:opacity-100 transition-opacity duration-200"
      style={isFeedbackMode ? { opacity: 1 } : undefined}
    >
      {/* Quick thumbs */}
      <Button
        variant="ghost"
        size="icon"
        className={`h-7 w-7 rounded-full ${currentRating === "good" ? "bg-emerald-100 text-emerald-600" : "text-muted-foreground hover:text-emerald-600"}`}
        onClick={() => handleQuickRating("good")}
        disabled={submitting}
      >
        <ThumbsUp className="w-3.5 h-3.5" />
      </Button>

      <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className={`h-7 w-7 rounded-full ${currentRating === "bad" ? "bg-red-100 text-red-600" : "text-muted-foreground hover:text-red-500"}`}
            onClick={() => handleQuickRating("bad")}
            disabled={submitting}
          >
            <ThumbsDown className="w-3.5 h-3.5" />
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
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">何が問題？</label>
              <TagSelector
                tags={tags}
                selected={selectedTags}
                onChange={setSelectedTags}
                sentiment={selectedRating === "good" ? "positive" : "negative"}
              />
            </div>

            {/* Dimension ratings (FB mode only) */}
            {isFeedbackMode && dimensions.length > 0 && (
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">多次元評価</label>
                <DimensionRating
                  dimensions={dimensions}
                  scores={dimensionScores}
                  onChange={setDimensionScores}
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

            {/* Correction (FB mode only) */}
            {isFeedbackMode && (
              <Textarea
                placeholder="修正案（正しい回答はこうあるべき）"
                value={correction}
                onChange={e => setCorrection(e.target.value)}
                className="text-sm min-h-[50px] resize-none"
              />
            )}

            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setPopoverOpen(false)}>
                キャンセル
              </Button>
              <Button size="sm" onClick={handleSubmitDetailed} disabled={submitting}>
                {submitting ? "送信中..." : "送信"}
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>

      {/* Detailed FB button */}
      {!submitted && !popoverOpen && (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
          onClick={() => {
            setSelectedRating(null);
            setPopoverOpen(true);
          }}
        >
          <MessageSquarePlus className="w-3.5 h-3.5 mr-1" />
          詳細FB
        </Button>
      )}

      {submitted && (
        <span className="text-[10px] text-muted-foreground ml-1">
          FB済み
        </span>
      )}
    </div>
  );
}
