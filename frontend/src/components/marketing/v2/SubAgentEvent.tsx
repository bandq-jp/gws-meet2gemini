"use client";

/**
 * Sub-Agent Event Component
 *
 * Displays sub-agent activity with agent name, event type, and status.
 */

import type { SubAgentActivityItem } from "@/lib/marketing/types";
import { Loader2, Check, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SubAgentEventProps {
  item: SubAgentActivityItem;
}

export function SubAgentEvent({ item }: SubAgentEventProps) {
  const isRunning = item.isRunning;

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm",
        isRunning
          ? "bg-purple-50 text-purple-700 dark:bg-purple-950 dark:text-purple-300"
          : "bg-slate-50 text-slate-700 dark:bg-slate-900 dark:text-slate-300"
      )}
    >
      {/* Agent icon */}
      <Bot className="w-4 h-4 flex-shrink-0" />

      {/* Agent name badge */}
      <span
        className={cn(
          "px-1.5 py-0.5 rounded text-xs font-medium",
          getAgentColor(item.agent)
        )}
      >
        {formatAgentName(item.agent)}
      </span>

      {/* Event description */}
      <span className="opacity-80">{getEventLabel(item.eventType)}</span>

      {/* Tool name if available */}
      {item.data?.tool_name && (
        <span className="font-mono text-xs bg-black/5 dark:bg-white/10 px-1 rounded">
          {item.data.tool_name}
        </span>
      )}

      {/* Status indicator */}
      <div className="ml-auto">
        {isRunning ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <Check className="w-3 h-3 text-green-600" />
        )}
      </div>
    </div>
  );
}

function formatAgentName(name: string): string {
  // Convert "AnalyticsAgent" to "Analytics"
  return name.replace(/Agent$/i, "").replace(/([a-z])([A-Z])/g, "$1 $2");
}

function getEventLabel(eventType: string): string {
  switch (eventType) {
    case "tool_called":
      return "Calling tool...";
    case "tool_output":
      return "Tool completed";
    case "reasoning":
      return "Analyzing...";
    case "text_delta":
      return "Generating response";
    case "message_output":
      return "Response ready";
    default:
      return eventType;
  }
}

function getAgentColor(agent: string): string {
  const name = agent.toLowerCase();

  if (name.includes("analytics") || name.includes("ga4")) {
    return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
  }
  if (name.includes("seo") || name.includes("ahrefs")) {
    return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
  }
  if (name.includes("ad") || name.includes("meta")) {
    return "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200";
  }
  if (name.includes("zoho") || name.includes("crm")) {
    return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200";
  }
  if (name.includes("wordpress") || name.includes("content")) {
    return "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200";
  }
  if (name.includes("candidate") || name.includes("insight")) {
    return "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200";
  }

  return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200";
}
