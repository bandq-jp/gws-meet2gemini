"use client";

import { Star } from "lucide-react";
import type { FeedbackDimension } from "@/lib/feedback/types";

interface DimensionRatingProps {
  dimensions: FeedbackDimension[];
  scores: Record<string, number>;
  onChange: (scores: Record<string, number>) => void;
}

export function DimensionRating({ dimensions, scores, onChange }: DimensionRatingProps) {
  const setScore = (key: string, value: number) => {
    onChange({ ...scores, [key]: value });
  };

  return (
    <div className="space-y-2">
      {dimensions.map(dim => {
        const current = scores[dim.key] || 0;
        const max = dim.max_value || 5;
        return (
          <div key={dim.key} className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground w-16 shrink-0">{dim.display_name}</span>
            <div className="flex gap-0.5">
              {Array.from({ length: max }, (_, i) => i + 1).map(n => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setScore(dim.key, n === current ? 0 : n)}
                  className="p-0.5 transition-transform hover:scale-110"
                >
                  <Star
                    className={`w-4 h-4 ${
                      n <= current
                        ? "fill-amber-400 text-amber-400"
                        : "text-gray-300"
                    }`}
                  />
                </button>
              ))}
            </div>
            {current > 0 && (
              <span className="text-[10px] text-muted-foreground">{current}/{max}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
