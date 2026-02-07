"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { TokenUsageDaily } from "@/lib/operations/types";

interface Props {
  daily: TokenUsageDaily[];
  loading: boolean;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function TokenUsageChart({ daily, loading }: Props) {
  if (loading) {
    return <div className="h-64 animate-pulse rounded bg-muted" />;
  }

  if (daily.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No token usage data for this period.
      </div>
    );
  }

  const totalInput = daily.reduce((s, d) => s + d.input_tokens, 0);
  const totalOutput = daily.reduce((s, d) => s + d.output_tokens, 0);
  const totalCost = daily.reduce((s, d) => s + d.estimated_cost_usd, 0);
  const totalTraces = daily.reduce((s, d) => s + d.trace_count, 0);

  const chartData = daily.map((d) => ({
    date: d.day.slice(5), // MM-DD
    input: d.input_tokens,
    output: d.output_tokens,
    cost: d.estimated_cost_usd,
  }));

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardHeader className="pb-1 pt-3 px-3">
            <CardTitle className="text-xs text-muted-foreground">Input Tokens</CardTitle>
          </CardHeader>
          <CardContent className="px-3 pb-3">
            <div className="text-xl font-bold">{formatTokens(totalInput)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1 pt-3 px-3">
            <CardTitle className="text-xs text-muted-foreground">Output Tokens</CardTitle>
          </CardHeader>
          <CardContent className="px-3 pb-3">
            <div className="text-xl font-bold">{formatTokens(totalOutput)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1 pt-3 px-3">
            <CardTitle className="text-xs text-muted-foreground">Est. Cost</CardTitle>
          </CardHeader>
          <CardContent className="px-3 pb-3">
            <div className="text-xl font-bold">${totalCost.toFixed(2)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1 pt-3 px-3">
            <CardTitle className="text-xs text-muted-foreground">Conversations</CardTitle>
          </CardHeader>
          <CardContent className="px-3 pb-3">
            <div className="text-xl font-bold">{totalTraces}</div>
          </CardContent>
        </Card>
      </div>

      {/* Area chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => formatTokens(v)} tick={{ fontSize: 11 }} />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                return (
                  <div className="rounded-lg border bg-background p-3 shadow-md">
                    <p className="font-medium text-sm">{label}</p>
                    <p className="text-sm text-violet-600">
                      Input: {formatTokens(payload[0]?.value as number || 0)}
                    </p>
                    <p className="text-sm text-emerald-600">
                      Output: {formatTokens(payload[1]?.value as number || 0)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Cost: ${(payload[0]?.payload?.cost || 0).toFixed(4)}
                    </p>
                  </div>
                );
              }}
            />
            <Area
              type="monotone"
              dataKey="input"
              stackId="1"
              stroke="#8b5cf6"
              fill="#8b5cf6"
              fillOpacity={0.3}
            />
            <Area
              type="monotone"
              dataKey="output"
              stackId="1"
              stroke="#10b981"
              fill="#10b981"
              fillOpacity={0.3}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Cost note */}
      <p className="text-xs text-muted-foreground">
        Gemini 3 Flash: $0.50/1M input, $3.00/1M output
      </p>
    </div>
  );
}
