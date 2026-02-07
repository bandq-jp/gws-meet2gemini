"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MessageSquare, Wrench, AlertTriangle, Clock } from "lucide-react";
import type { AnalyticsOverview } from "@/lib/operations/types";

interface Props {
  data: AnalyticsOverview | null;
  loading: boolean;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatDuration(ms: number): string {
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`;
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

const CARDS = [
  {
    key: "conversations",
    title: "Conversations",
    icon: MessageSquare,
    color: "text-blue-600",
    bg: "bg-blue-50",
    getValue: (d: AnalyticsOverview) => formatNumber(d.total_conversations),
    getSub: (d: AnalyticsOverview) => `${d.unique_users} users`,
  },
  {
    key: "tools",
    title: "Tool Calls",
    icon: Wrench,
    color: "text-violet-600",
    bg: "bg-violet-50",
    getValue: (d: AnalyticsOverview) => formatNumber(d.total_tool_calls),
    getSub: (d: AnalyticsOverview) => `${formatNumber(d.total_llm_calls)} LLM calls`,
  },
  {
    key: "errors",
    title: "Error Rate",
    icon: AlertTriangle,
    color: "text-red-600",
    bg: "bg-red-50",
    getValue: (d: AnalyticsOverview) => `${d.error_rate}%`,
    getSub: (d: AnalyticsOverview) => `${d.error_count} errors`,
  },
  {
    key: "duration",
    title: "Avg Response",
    icon: Clock,
    color: "text-amber-600",
    bg: "bg-amber-50",
    getValue: (d: AnalyticsOverview) => formatDuration(d.avg_duration_ms),
    getSub: (d: AnalyticsOverview) =>
      `${formatNumber(d.total_input_tokens + d.total_output_tokens)} tokens`,
  },
];

export function OverviewCards({ data, loading }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      {CARDS.map((card) => (
        <Card key={card.key}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className={`rounded-md p-2 ${card.bg}`}>
              <card.icon className={`h-4 w-4 ${card.color}`} />
            </div>
          </CardHeader>
          <CardContent>
            {loading || !data ? (
              <div className="h-8 w-24 animate-pulse rounded bg-muted" />
            ) : (
              <>
                <div className="text-2xl font-bold">{card.getValue(data)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {card.getSub(data)}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
