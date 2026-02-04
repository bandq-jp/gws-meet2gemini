"use client";

/**
 * Tool Badge Component
 *
 * Displays a tool call with its status (running/complete).
 */

import type { ToolActivityItem } from "@/lib/marketing/types";
import { Loader2, Check, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ToolBadgeProps {
  item: ToolActivityItem;
}

export function ToolBadge({ item }: ToolBadgeProps) {
  // Use output presence to determine status (undefined = running, string = complete)
  const isRunning = !item.output;

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm",
        isRunning
          ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
          : "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"
      )}
    >
      {/* Icon */}
      <div className="flex-shrink-0">
        {isRunning ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Check className="w-4 h-4" />
        )}
      </div>

      {/* Tool name */}
      <div className="flex items-center gap-1.5">
        <Wrench className="w-3.5 h-3.5 opacity-70" />
        <span className="font-medium">{formatToolName(item.name)}</span>
      </div>

      {/* Status */}
      <span className="text-xs opacity-70">
        {isRunning ? "Running..." : "Done"}
      </span>
    </div>
  );
}

function formatToolName(name: string): string {
  // Convert snake_case or camelCase to readable format
  return name
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
