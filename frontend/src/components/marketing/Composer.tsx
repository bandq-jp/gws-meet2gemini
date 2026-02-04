"use client";

/**
 * Composer Component
 *
 * ChatGPT-style message input with auto-resize and send/stop functionality.
 * Based on ga4-oauth-aiagent reference implementation.
 */

import { useState, useRef, useCallback } from "react";
import { Send, Square } from "lucide-react";

export interface ComposerProps {
  onSend: (content: string) => Promise<void>;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function Composer({
  onSend,
  onStop,
  isStreaming = false,
  disabled = false,
  placeholder = "マーケティングデータについて質問...",
}: ComposerProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || disabled) return;

    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    await onSend(trimmed);
  }, [input, isStreaming, disabled, onSend]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 150) + "px";
  }, []);

  const handleStopClick = useCallback(() => {
    onStop?.();
  }, [onStop]);

  return (
    <div className="shrink-0 px-3 sm:px-6 pb-2 sm:pb-4 pt-2 bg-background safe-bottom">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-0 bg-white border border-[#d1d5db] rounded-2xl shadow-sm focus-within:border-[#9ca3af] focus-within:shadow-md transition-all">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="flex-1 min-h-[44px] max-h-[150px] resize-none bg-transparent px-4 py-3 text-[14px] sm:text-sm leading-relaxed placeholder:text-[#9ca3af] text-[#1a1a2e] outline-none disabled:opacity-40 disabled:cursor-not-allowed"
          />
          {isStreaming ? (
            <button
              onClick={handleStopClick}
              className="shrink-0 w-9 h-9 m-1.5 rounded-xl flex items-center justify-center bg-[#f0f1f5] hover:bg-[#e5e7eb] transition-colors cursor-pointer"
              aria-label="停止"
            >
              <Square className="w-4 h-4 text-[#e94560]" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || disabled}
              className="shrink-0 w-9 h-9 m-1.5 rounded-xl flex items-center justify-center bg-[#1a1a2e] hover:bg-[#2a2a4e] disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
              aria-label="送信"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          )}
        </div>
        <p className="hidden sm:block text-center text-[11px] text-[#9ca3af] mt-2">
          Shift+Enter で改行 / Enter で送信
        </p>
      </div>
    </div>
  );
}
