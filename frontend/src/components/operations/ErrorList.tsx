"use client";

import { Badge } from "@/components/ui/badge";
import { AlertTriangle } from "lucide-react";
import type { AgentError } from "@/lib/operations/types";

interface Props {
  errors: AgentError[];
  loading: boolean;
  onSelectTrace: (traceId: string) => void;
}

function formatTime(iso: string): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function ErrorList({ errors, loading, onSelectTrace }: Props) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-12 animate-pulse rounded bg-muted" />
        ))}
      </div>
    );
  }

  if (errors.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No errors for this period.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {errors.map((err) => (
        <div
          key={`${err.trace_id}-${err.span_id}`}
          className="rounded-lg border border-red-200 bg-red-50/50 p-3 cursor-pointer hover:bg-red-50 transition-colors"
          onClick={() => onSelectTrace(err.trace_id)}
        >
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs text-muted-foreground">
                  {formatTime(err.started_at)}
                </span>
                {err.agent_name && (
                  <Badge variant="secondary" className="text-xs">
                    {err.agent_name.replace("Agent", "")}
                  </Badge>
                )}
                {err.tool_name && (
                  <Badge variant="outline" className="text-xs font-mono">
                    {err.tool_name}
                  </Badge>
                )}
                <Badge variant="outline" className="text-xs">
                  {err.operation_name}
                </Badge>
              </div>
              <p className="text-sm text-red-800 break-all">
                {err.error_message || "Unknown error"}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
