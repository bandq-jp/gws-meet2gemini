"use client";

import { useState, useEffect } from "react";

// Phase-based thinking labels for better user feedback
const LABELS = [
  "リクエストを理解しています",
  "最適なエージェントを選択中",
  "データソースを確認中",
  "分析方針を策定中",
  "結果を準備しています",
];

const LABEL_INTERVAL_MS = 2500; // Faster rotation for better perceived progress

export function ThinkingIndicator() {
  const [labelIndex, setLabelIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setLabelIndex((prev) => (prev + 1) % LABELS.length);
    }, LABEL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

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
        key={labelIndex}
        className="thinking-label text-[12px] text-[#9ca3af] font-light tracking-wide"
      >
        {LABELS[labelIndex]}
      </span>
    </div>
  );
}
