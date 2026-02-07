"use client";

import type { PeriodFilter } from "@/lib/operations/types";

const OPTIONS: { value: PeriodFilter; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "7d" },
  { value: "30d", label: "30d" },
  { value: "all", label: "All" },
];

interface Props {
  value: PeriodFilter;
  onChange: (v: PeriodFilter) => void;
}

export function PeriodFilterToggle({ value, onChange }: Props) {
  return (
    <div className="inline-flex rounded-lg border bg-muted p-0.5">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
            value === opt.value
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
