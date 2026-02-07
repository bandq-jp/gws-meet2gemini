"use client";

/**
 * Feedback Hook
 *
 * Manages message-level feedback and annotations for the chat page.
 * Uses the same token management as use-marketing-chat-v2.
 */

import { useCallback, useRef, useState } from "react";
import type {
  MessageFeedback,
  MessageAnnotation,
  FeedbackCreatePayload,
  AnnotationCreatePayload,
  FeedbackTag,
  FeedbackDimension,
  FeedbackOverview,
  FeedbackListResponse,
} from "@/lib/feedback/types";

const CLIENT_SECRET_HEADER = "x-marketing-client-secret";

function getHeaders(secret: string): Record<string, string> {
  return {
    [CLIENT_SECRET_HEADER]: secret,
    "Content-Type": "application/json",
  };
}

// ============================================================
// Chat Page Hook (per-conversation feedback state)
// ============================================================

export function useFeedback(getClientSecret: () => string | null) {
  const [feedbackByMessage, setFeedbackByMessage] = useState<Record<string, MessageFeedback>>({});
  const [annotationsByMessage, setAnnotationsByMessage] = useState<Record<string, MessageAnnotation[]>>({});
  const [isFeedbackMode, setIsFeedbackMode] = useState(false);
  const [tags, setTags] = useState<FeedbackTag[]>([]);
  const [dimensions, setDimensions] = useState<FeedbackDimension[]>([]);
  const masterLoaded = useRef(false);

  const getHeadersSafe = useCallback((): Record<string, string> | null => {
    const secret = getClientSecret();
    if (!secret) return null;
    return getHeaders(secret);
  }, [getClientSecret]);

  // Load master data (tags + dimensions) once
  const loadMasterData = useCallback(async () => {
    if (masterLoaded.current) return;
    const h = getHeadersSafe();
    if (!h) return; // token not ready yet — will retry later
    masterLoaded.current = true;
    try {
      const [tagsRes, dimRes] = await Promise.all([
        fetch("/api/feedback/tags", { headers: h }),
        fetch("/api/feedback/dimensions", { headers: h }),
      ]);
      if (tagsRes.ok) setTags(await tagsRes.json());
      if (dimRes.ok) setDimensions(await dimRes.json());
    } catch {
      masterLoaded.current = false;
    }
  }, [getHeadersSafe]);

  // Load all feedback for a conversation
  const loadConversationFeedback = useCallback(async (conversationId: string) => {
    const h = getHeadersSafe();
    if (!h) return; // token not ready yet
    try {
      const res = await fetch(`/api/feedback/conversation/${conversationId}`, {
        headers: h,
      });
      if (!res.ok) return;
      const data = await res.json();

      const fbMap: Record<string, MessageFeedback> = {};
      for (const fb of data.feedback || []) {
        fbMap[fb.message_id] = fb;
      }
      setFeedbackByMessage(fbMap);

      const annMap: Record<string, MessageAnnotation[]> = {};
      for (const ann of data.annotations || []) {
        if (!annMap[ann.message_id]) annMap[ann.message_id] = [];
        annMap[ann.message_id].push(ann);
      }
      setAnnotationsByMessage(annMap);
    } catch (err) {
      console.error("Failed to load feedback:", err);
    }
  }, [getHeadersSafe]);

  // Submit message-level feedback
  const submitFeedback = useCallback(async (messageId: string, payload: FeedbackCreatePayload) => {
    const h = getHeadersSafe();
    if (!h) throw new Error("No client secret");
    const res = await fetch(`/api/feedback/messages/${messageId}`, {
      method: "POST",
      headers: h,
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to submit feedback");
    const fb: MessageFeedback = await res.json();
    setFeedbackByMessage(prev => ({ ...prev, [messageId]: fb }));
    return fb;
  }, [getHeadersSafe]);

  // Create annotation
  const createAnnotation = useCallback(async (payload: AnnotationCreatePayload) => {
    const h = getHeadersSafe();
    if (!h) throw new Error("No client secret");
    const res = await fetch("/api/feedback/annotations", {
      method: "POST",
      headers: h,
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to create annotation");
    const ann: MessageAnnotation = await res.json();
    setAnnotationsByMessage(prev => ({
      ...prev,
      [ann.message_id]: [...(prev[ann.message_id] || []), ann],
    }));
    return ann;
  }, [getHeadersSafe]);

  // Delete annotation
  const deleteAnnotation = useCallback(async (annotationId: string, messageId: string) => {
    const h = getHeadersSafe();
    if (!h) return;
    try {
      await fetch(`/api/feedback/annotations/${annotationId}`, {
        method: "DELETE",
        headers: h,
      });
      setAnnotationsByMessage(prev => ({
        ...prev,
        [messageId]: (prev[messageId] || []).filter(a => a.id !== annotationId),
      }));
    } catch (err) {
      console.error("Failed to delete annotation:", err);
    }
  }, [getHeadersSafe]);

  // Clear state (when switching conversations)
  const clearFeedback = useCallback(() => {
    setFeedbackByMessage({});
    setAnnotationsByMessage({});
  }, []);

  return {
    feedbackByMessage,
    annotationsByMessage,
    isFeedbackMode,
    setIsFeedbackMode,
    tags,
    dimensions,
    loadMasterData,
    loadConversationFeedback,
    submitFeedback,
    createAnnotation,
    deleteAnnotation,
    clearFeedback,
  };
}

// ============================================================
// Dashboard Hook (feedback review page)
// ============================================================

export function useFeedbackDashboard(getClientSecret: () => string | null) {
  const [overview, setOverview] = useState<FeedbackOverview | null>(null);
  const [listData, setListData] = useState<FeedbackListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [tags, setTags] = useState<FeedbackTag[]>([]);

  const getHeadersSafe = useCallback((): Record<string, string> | null => {
    const secret = getClientSecret();
    if (!secret) return null;
    return getHeaders(secret);
  }, [getClientSecret]);

  const loadOverview = useCallback(async (days = 30) => {
    const h = getHeadersSafe();
    if (!h) return;
    setLoading(true);
    try {
      const [overviewRes, tagsRes] = await Promise.all([
        fetch(`/api/feedback/overview?days=${days}`, { headers: h }),
        fetch("/api/feedback/tags", { headers: h }),
      ]);
      if (overviewRes.ok) setOverview(await overviewRes.json());
      if (tagsRes.ok) setTags(await tagsRes.json());
    } finally {
      setLoading(false);
    }
  }, [getHeadersSafe]);

  const loadList = useCallback(async (params: {
    page?: number;
    rating?: string;
    review_status?: string;
    tag?: string;
  } = {}) => {
    const h = getHeadersSafe();
    if (!h) return;
    setLoading(true);
    try {
      const sp = new URLSearchParams();
      if (params.page) sp.set("page", String(params.page));
      if (params.rating) sp.set("rating", params.rating);
      if (params.review_status) sp.set("review_status", params.review_status);
      if (params.tag) sp.set("tag", params.tag);
      const res = await fetch(`/api/feedback/list?${sp}`, { headers: h });
      if (res.ok) setListData(await res.json());
    } finally {
      setLoading(false);
    }
  }, [getHeadersSafe]);

  const updateReview = useCallback(async (feedbackId: string, reviewStatus: string, notes?: string) => {
    const h = getHeadersSafe();
    if (!h) return false;
    try {
      const res = await fetch(`/api/feedback/${feedbackId}/review`, {
        method: "PUT",
        headers: h,
        body: JSON.stringify({ review_status: reviewStatus, review_notes: notes }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }, [getHeadersSafe]);

  const exportFeedback = useCallback(async (format: "jsonl" | "csv", filters?: {
    rating?: string;
    review_status?: string;
    tag?: string;
  }) => {
    const h = getHeadersSafe();
    if (!h) throw new Error("No client secret");
    const sp = new URLSearchParams({ format });
    if (filters?.rating) sp.set("rating", filters.rating);
    if (filters?.review_status) sp.set("review_status", filters.review_status);
    if (filters?.tag) sp.set("tag", filters.tag);
    const res = await fetch(`/api/feedback/export?${sp}`, { headers: h });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `feedback_${new Date().toISOString().slice(0, 10)}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }, [getHeadersSafe]);

  return {
    overview,
    listData,
    loading,
    tags,
    loadOverview,
    loadList,
    updateReview,
    exportFeedback,
  };
}
