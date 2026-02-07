"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight, Bot, Brain, Wrench, ArrowRight, AlertCircle } from "lucide-react";
import type { SpanDetail } from "@/lib/operations/types";

const OP_ICONS: Record<string, typeof Bot> = {
  invoke_agent: Bot,
  call_llm: Brain,
  execute_tool: Wrench,
  send_data: ArrowRight,
};

const OP_COLORS: Record<string, string> = {
  invoke_agent: "text-blue-600",
  call_llm: "text-violet-600",
  execute_tool: "text-emerald-600",
  send_data: "text-gray-500",
};

function formatDuration(ms: number | null): string {
  if (ms === null) return "";
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(2)}s`;
  return `${Math.round(ms)}ms`;
}

interface SpanNodeProps {
  span: SpanDetail;
  depth: number;
  traceStart: number;
  traceDuration: number;
}

function SpanNode({ span, depth, traceStart, traceDuration }: SpanNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = span.children && span.children.length > 0;
  const Icon = OP_ICONS[span.operation_name] || ArrowRight;
  const color = OP_COLORS[span.operation_name] || "text-gray-500";
  const isError = span.status === "error";

  // Waterfall bar positioning
  const spanStart = new Date(span.started_at).getTime();
  const spanDuration = span.duration_ms || 0;
  const leftPct = traceDuration > 0 ? ((spanStart - traceStart) / traceDuration) * 100 : 0;
  const widthPct = traceDuration > 0 ? (spanDuration / traceDuration) * 100 : 0;

  const label = span.tool_name || span.agent_name || span.operation_name;

  return (
    <div>
      <div
        className={`flex items-center gap-1 py-1 px-1 rounded hover:bg-muted/50 cursor-pointer ${
          isError ? "bg-red-50" : ""
        }`}
        style={{ paddingLeft: `${depth * 20 + 4}px` }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {/* Expand toggle */}
        <span className="w-4 shrink-0">
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            )
          ) : null}
        </span>

        {/* Icon */}
        <Icon className={`h-3.5 w-3.5 shrink-0 ${isError ? "text-red-500" : color}`} />

        {/* Label */}
        <span className={`text-sm truncate max-w-[200px] ${isError ? "text-red-700 font-medium" : ""}`}>
          {label}
        </span>

        {/* Error indicator */}
        {isError && <AlertCircle className="h-3 w-3 text-red-500 shrink-0" />}

        {/* Tokens */}
        {(span.input_tokens || span.output_tokens) && (
          <Badge variant="outline" className="text-[10px] ml-1 shrink-0">
            {span.input_tokens || 0}→{span.output_tokens || 0}
          </Badge>
        )}

        {/* Waterfall bar */}
        <div className="flex-1 mx-2 h-4 relative">
          <div
            className={`absolute top-0.5 h-3 rounded-sm ${
              isError ? "bg-red-400" : span.operation_name === "call_llm" ? "bg-violet-400" : "bg-emerald-400"
            }`}
            style={{
              left: `${Math.max(0, Math.min(leftPct, 100))}%`,
              width: `${Math.max(1, Math.min(widthPct, 100 - leftPct))}%`,
            }}
          />
        </div>

        {/* Duration */}
        <span className="text-xs font-mono text-muted-foreground shrink-0 w-16 text-right">
          {formatDuration(span.duration_ms)}
        </span>
      </div>

      {/* Children */}
      {expanded &&
        hasChildren &&
        span.children!.map((child) => (
          <SpanNode
            key={child.span_id}
            span={child}
            depth={depth + 1}
            traceStart={traceStart}
            traceDuration={traceDuration}
          />
        ))}
    </div>
  );
}

interface Props {
  spans: SpanDetail[];
}

export function SpanTree({ spans }: Props) {
  if (spans.length === 0) {
    return <div className="text-sm text-muted-foreground py-4 text-center">No spans</div>;
  }

  // Calculate trace time range
  const allStartTimes = spans
    .map((s) => new Date(s.started_at).getTime())
    .filter((t) => !isNaN(t));
  const traceStart = Math.min(...allStartTimes);
  const allEndTimes = spans
    .filter((s) => s.ended_at)
    .map((s) => new Date(s.ended_at!).getTime());
  const traceEnd = allEndTimes.length > 0 ? Math.max(...allEndTimes) : traceStart + 1000;
  const traceDuration = traceEnd - traceStart;

  return (
    <div className="rounded-md border bg-background p-2">
      {spans.map((span) => (
        <SpanNode
          key={span.span_id}
          span={span}
          depth={0}
          traceStart={traceStart}
          traceDuration={traceDuration}
        />
      ))}
    </div>
  );
}
