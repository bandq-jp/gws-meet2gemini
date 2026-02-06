"use client";

import { useState, useEffect, useRef } from "react";

// Fallback label: shown only until the first real progress event arrives from backend.
// Typically visible for <500ms (time between SSE connection and first progress event).
const FALLBACK_LABEL = "処理を開始しています...";

// After a real progress event, if no new event arrives within this timeout,
// show a generic continuation label to indicate the system is still working.
const STALE_TIMEOUT_MS = 8000;
const STALE_LABEL = "処理中...";

interface ThinkingIndicatorProps {
  /** Real progress text from backend SSE events */
  progressText?: string;
}

export function ThinkingIndicator({ progressText }: ThinkingIndicatorProps) {
  const [isStale, setIsStale] = useState(false);
  const staleTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastProgressRef = useRef(progressText);

  // Reset stale timer when progressText changes
  useEffect(() => {
    if (progressText && progressText !== lastProgressRef.current) {
      lastProgressRef.current = progressText;
      setIsStale(false);

      // Start stale timer: if no new progress arrives, show generic label
      if (staleTimerRef.current) clearTimeout(staleTimerRef.current);
      staleTimerRef.current = setTimeout(() => setIsStale(true), STALE_TIMEOUT_MS);
    }

    return () => {
      if (staleTimerRef.current) clearTimeout(staleTimerRef.current);
    };
  }, [progressText]);

  // Determine displayed label:
  // 1. If backend sent progress text and it's fresh → show it
  // 2. If progress text is stale (no update for 8s) → show generic "処理中..."
  // 3. If no progress text yet → show fallback
  const displayLabel = progressText
    ? isStale
      ? STALE_LABEL
      : progressText
    : FALLBACK_LABEL;

  return (
    <div
      className="thinking-indicator flex items-center gap-2.5 py-2"
      role="status"
      aria-label="AIが考えています"
    >
      <div className="flex items-center gap-[5px]">
        <span className="thinking-dot thinking-dot-1" />
        <span className="thinking-dot thinking-dot-2" />
        <span className="thinking-dot thinking-dot-3" />
      </div>
      <span
        key={displayLabel}
        className="thinking-label text-[12px] text-[#9ca3af] font-light tracking-wide"
      >
        {displayLabel}
      </span>
    </div>
  );
}
