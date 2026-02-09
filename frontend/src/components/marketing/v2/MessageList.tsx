"use client";

/**
 * MessageList Component
 *
 * Renders the scrollable message container with smart auto-scroll.
 * - Only auto-scrolls when a NEW message is added (user sends message)
 * - Does NOT auto-scroll during streaming updates
 * - If user scrolls up, auto-scroll is disabled until user sends a new message
 * - Shows "scroll to bottom" button when user has scrolled away during streaming
 *
 * Based on ga4-oauth-aiagent reference implementation.
 */

import { useEffect, useRef, useCallback, useState } from "react";
import { ChevronDown } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import type { Message } from "@/lib/marketing/types";
import type {
  FeedbackTag,
  MessageFeedback,
  MessageAnnotation,
  FeedbackCreatePayload,
  AnnotationCreatePayload,
} from "@/lib/feedback/types";

export interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  // Ask user clarification callback
  onSendMessage?: (content: string) => void;
  // Feedback props
  feedbackByMessage?: Record<string, MessageFeedback>;
  annotationsByMessage?: Record<string, MessageAnnotation[]>;
  feedbackTags?: FeedbackTag[];
  isFeedbackMode?: boolean;
  conversationId?: string | null;
  activeAnnotationId?: string | null;
  onSubmitFeedback?: (messageId: string, payload: FeedbackCreatePayload) => Promise<unknown>;
  onCreateAnnotation?: (payload: AnnotationCreatePayload) => Promise<unknown>;
  onDeleteAnnotation?: (annotationId: string, messageId: string) => Promise<void>;
  onSetActiveAnnotation?: (annotationId: string | null) => void;
}

export function MessageList({
  messages,
  isStreaming,
  onSendMessage,
  feedbackByMessage,
  annotationsByMessage,
  feedbackTags,
  isFeedbackMode,
  conversationId,
  activeAnnotationId,
  onSubmitFeedback,
  onCreateAnnotation,
  onDeleteAnnotation,
  onSetActiveAnnotation,
}: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastMessageCountRef = useRef(0);
  const isNearBottomRef = useRef(true);
  // Track if user has intentionally scrolled away from bottom
  const userScrolledAwayRef = useRef(false);
  // State for showing "scroll to bottom" button
  const [showScrollButton, setShowScrollButton] = useState(false);

  // Check if user is near bottom (within 200px)
  const checkIfNearBottom = useCallback(() => {
    if (!scrollRef.current) return true;
    const el = scrollRef.current;
    const threshold = 200; // Increased from 150 for more forgiving detection
    return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  }, []);

  // Handle scroll events - track if user scrolled away
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;

    const isNearBottom = checkIfNearBottom();
    isNearBottomRef.current = isNearBottom;

    // If user scrolled up (not near bottom), mark as scrolled away
    if (!isNearBottom) {
      userScrolledAwayRef.current = true;
      setShowScrollButton(true);
    } else {
      // If user scrolled back to bottom, reset the flag
      userScrolledAwayRef.current = false;
      setShowScrollButton(false);
    }
  }, [checkIfNearBottom]);

  // Set up scroll listener
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  // Auto-scroll ONLY when a new message is added (not during streaming updates)
  useEffect(() => {
    if (!scrollRef.current) return;

    const messageCount = messages.length;
    const isNewMessage = messageCount > lastMessageCountRef.current;
    const prevCount = lastMessageCountRef.current;
    lastMessageCountRef.current = messageCount;

    // Only scroll on NEW message (user sent message or first assistant response)
    // This prevents forced scrolling during streaming content updates
    if (isNewMessage && prevCount > 0) {
      // Check if the new message is from the user (they just sent a message)
      const lastMessage = messages[messages.length - 1];
      const isUserMessage = lastMessage?.role === "user";

      if (isUserMessage) {
        // User sent a message - reset scroll state and scroll to bottom
        userScrolledAwayRef.current = false;
        setShowScrollButton(false);
        const el = scrollRef.current;
        requestAnimationFrame(() => {
          el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
        });
      } else if (!userScrolledAwayRef.current) {
        // New assistant message and user hasn't scrolled away - scroll to bottom
        const el = scrollRef.current;
        requestAnimationFrame(() => {
          el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
        });
      }
    } else if (messageCount === 1) {
      // First message - always scroll
      const el = scrollRef.current;
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [messages]);

  // Handle "scroll to bottom" button click
  const scrollToBottom = useCallback(() => {
    if (!scrollRef.current) return;
    userScrolledAwayRef.current = false;
    setShowScrollButton(false);
    scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, []);

  return (
    <div className="relative flex-1 overflow-hidden">
      <div ref={scrollRef} className="h-full overflow-y-auto overflow-x-hidden">
        <div className="max-w-3xl mx-auto py-4 sm:py-6 px-4 sm:px-6 space-y-5 sm:space-y-6 min-w-0">
          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              message={msg}
              feedback={feedbackByMessage?.[msg.id]}
              annotations={annotationsByMessage?.[msg.id]}
              feedbackTags={feedbackTags}
              isFeedbackMode={isFeedbackMode}
              conversationId={conversationId || undefined}
              activeAnnotationId={activeAnnotationId}
              onSendMessage={onSendMessage}
              onSubmitFeedback={onSubmitFeedback}
              onCreateAnnotation={onCreateAnnotation}
              onDeleteAnnotation={onDeleteAnnotation}
              onSetActiveAnnotation={onSetActiveAnnotation}
            />
          ))}
        </div>
      </div>

      {/* Scroll to bottom button - shown when user has scrolled away during streaming */}
      {showScrollButton && isStreaming && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 right-4 flex items-center gap-1.5 bg-background/90 backdrop-blur-sm border border-border rounded-full px-4 py-2.5 sm:px-3 sm:py-1.5 shadow-lg hover:bg-background transition-colors text-xs text-muted-foreground"
          aria-label="最下部へスクロール"
        >
          <ChevronDown className="h-3.5 w-3.5" />
          <span>最新へ</span>
        </button>
      )}
    </div>
  );
}
