"use client";

/**
 * MessageList Component
 *
 * Renders the scrollable message container with smart auto-scroll.
 * Only scrolls when user is already near the bottom.
 * Based on ga4-oauth-aiagent reference implementation.
 */

import { useEffect, useRef, useCallback } from "react";
import { ChatMessage } from "./ChatMessage";
import type { Message } from "@/lib/marketing/types";

export interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
}

export function MessageList({ messages, isStreaming }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastMessageCountRef = useRef(0);
  const isNearBottomRef = useRef(true);

  // Check if user is near bottom (within 150px)
  const checkIfNearBottom = useCallback(() => {
    if (!scrollRef.current) return true;
    const el = scrollRef.current;
    const threshold = 150;
    return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  }, []);

  // Update near-bottom status on scroll
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    const handleScroll = () => {
      isNearBottomRef.current = checkIfNearBottom();
    };

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, [checkIfNearBottom]);

  // Auto-scroll only when new message is added or user is near bottom during streaming
  useEffect(() => {
    if (!scrollRef.current) return;

    const messageCount = messages.length;
    const isNewMessage = messageCount > lastMessageCountRef.current;
    lastMessageCountRef.current = messageCount;

    // Scroll if: new message added, OR already near bottom while streaming
    if (isNewMessage || (isStreaming && isNearBottomRef.current)) {
      const el = scrollRef.current;
      // Use requestAnimationFrame for smoother scrolling
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [messages, isStreaming]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden">
      <div className="max-w-3xl mx-auto py-4 sm:py-6 px-4 sm:px-6 space-y-5 sm:space-y-6 min-w-0">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
      </div>
    </div>
  );
}
