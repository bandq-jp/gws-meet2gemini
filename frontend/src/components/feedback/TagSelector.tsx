"use client";

import type { FeedbackTag } from "@/lib/feedback/types";

interface TagSelectorProps {
  tags: FeedbackTag[];
  selected: string[];
  onChange: (tags: string[]) => void;
  sentiment?: "positive" | "negative" | "neutral" | "all";
}

export function TagSelector({ tags, selected, onChange, sentiment = "all" }: TagSelectorProps) {
  const filtered = sentiment === "all" ? tags : tags.filter(t => t.sentiment === sentiment);

  const toggle = (key: string) => {
    onChange(
      selected.includes(key) ? selected.filter(k => k !== key) : [...selected, key]
    );
  };

  return (
    <div className="flex flex-wrap gap-1.5">
      {filtered.map(tag => {
        const isSelected = selected.includes(tag.key);
        return (
          <button
            key={tag.key}
            type="button"
            onClick={() => toggle(tag.key)}
            className={`
              inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-all
              ${isSelected
                ? "ring-2 ring-offset-1 shadow-sm"
                : "opacity-70 hover:opacity-100"
              }
            `}
            style={{
              backgroundColor: isSelected ? `${tag.color}20` : "#f3f4f6",
              color: isSelected ? (tag.color || "#374151") : "#6b7280",
              "--tw-ring-color": tag.color || undefined,
            } as React.CSSProperties}
          >
            {tag.display_name}
            {isSelected && (
              <span className="ml-0.5 text-[10px]">&times;</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
