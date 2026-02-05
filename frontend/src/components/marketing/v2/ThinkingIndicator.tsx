"use client";

import { useState, useEffect, useRef } from "react";

// Concrete, action-oriented labels that show what's actually happening
// Ordered to match the actual system flow: init → routing → connection → execution → synthesis
const LABELS = [
  "メッセージを分析中...",
  "専門エージェントを選択中...",
  "データソースに接続中...",
  "情報を取得しています...",
  "分析を実行中...",
  "結果を整理しています...",
];

// Progressive intervals: start fast (feels responsive), slow down (feels stable)
// Total cycle: 1.2 + 1.5 + 2.0 + 2.5 + 3.0 + 3.5 = 13.7s before repeat
const INTERVALS_MS = [1200, 1500, 2000, 2500, 3000, 3500];

export function ThinkingIndicator() {
  const [labelIndex, setLabelIndex] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const scheduleNext = (currentIndex: number) => {
      const interval = INTERVALS_MS[currentIndex] || INTERVALS_MS[INTERVALS_MS.length - 1];
      timerRef.current = setTimeout(() => {
        const nextIndex = (currentIndex + 1) % LABELS.length;
        setLabelIndex(nextIndex);
        scheduleNext(nextIndex);
      }, interval);
    };

    scheduleNext(labelIndex);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
