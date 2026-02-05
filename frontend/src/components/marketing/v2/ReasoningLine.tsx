"use client";

/**
 * Reasoning Line Component
 *
 * Displays agent reasoning/thinking content.
 */

import type { ReasoningActivityItem } from "@/lib/marketing/types";
import { Brain } from "lucide-react";

export interface ReasoningLineProps {
  item: ReasoningActivityItem;
}

export function ReasoningLine({ item }: ReasoningLineProps) {
  if (!item.content) return null;

  return (
    <div className="flex items-start gap-2 px-3 py-2 bg-amber-50 dark:bg-amber-950 rounded-md text-sm text-amber-800 dark:text-amber-200">
      <Brain className="w-4 h-4 flex-shrink-0 mt-0.5 opacity-70" />
      <p className="italic leading-relaxed">{item.content}</p>
    </div>
  );
}
