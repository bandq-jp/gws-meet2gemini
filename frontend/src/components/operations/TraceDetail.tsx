"use client";

import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ExternalLink, Clock, Cpu, Wrench, AlertTriangle } from "lucide-react";
import { useTraceDetail } from "@/hooks/use-agent-analytics";
import { SpanTree } from "./SpanTree";

interface Props {
  traceId: string | null;
  onClose: () => void;
  phoenixUrl?: string;
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "-";
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`;
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(2)}s`;
  return `${Math.round(ms)}ms`;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function TraceDetail({ traceId, onClose, phoenixUrl }: Props) {
  const { data, loading } = useTraceDetail(traceId);

  return (
    <Sheet open={!!traceId} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            Trace Detail
            {phoenixUrl && traceId && (
              <a
                href={`${phoenixUrl}/tracing/traces/${traceId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-normal text-muted-foreground hover:text-foreground"
              >
                <ExternalLink className="h-4 w-4 inline mr-1" />
                Phoenix
              </a>
            )}
          </SheetTitle>
        </SheetHeader>

        {loading && (
          <div className="space-y-3 mt-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-muted" />
            ))}
          </div>
        )}

        {data && (
          <div className="space-y-6 mt-4">
            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <Clock className="h-3 w-3" />
                  Duration
                </div>
                <div className="text-lg font-semibold">
                  {formatDuration(data.trace.duration_ms)}
                </div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <Cpu className="h-3 w-3" />
                  LLM Calls
                </div>
                <div className="text-lg font-semibold">{data.trace.total_llm_calls}</div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <Wrench className="h-3 w-3" />
                  Tool Calls
                </div>
                <div className="text-lg font-semibold">{data.trace.total_tool_calls}</div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  Tokens
                </div>
                <div className="text-lg font-semibold">
                  {formatTokens(data.trace.total_input_tokens + data.trace.total_output_tokens)}
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatTokens(data.trace.total_input_tokens)} in / {formatTokens(data.trace.total_output_tokens)} out
                </div>
              </div>
            </div>

            {/* Meta info */}
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">User</span>
                <span>{data.trace.user_email || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <Badge variant={data.trace.status === "ok" ? "secondary" : "destructive"}>
                  {data.trace.status}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Trace ID</span>
                <span className="font-mono text-xs">{data.trace.trace_id.slice(0, 16)}...</span>
              </div>
              {data.trace.error_message && (
                <div className="mt-2 rounded-md bg-red-50 p-3 text-sm text-red-800 flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                  {data.trace.error_message}
                </div>
              )}
            </div>

            {/* Agents used */}
            {data.trace.sub_agents_used && data.trace.sub_agents_used.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2">Sub-agents</h4>
                <div className="flex flex-wrap gap-1.5">
                  {data.trace.sub_agents_used.map((a) => (
                    <Badge key={a} variant="secondary">{a.replace("Agent", "")}</Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Span tree */}
            <div>
              <h4 className="text-sm font-medium mb-2">
                Span Tree ({data.spans.length} spans)
              </h4>
              <SpanTree spans={data.tree} />
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
