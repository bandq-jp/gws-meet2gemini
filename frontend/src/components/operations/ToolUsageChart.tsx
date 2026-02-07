"use client";

import { Badge } from "@/components/ui/badge";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { ToolUsageStat } from "@/lib/operations/types";

interface Props {
  tools: ToolUsageStat[];
  loading: boolean;
}

const COLORS = [
  "#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#ec4899", "#6366f1", "#14b8a6", "#f97316", "#84cc16",
];

export function ToolUsageChart({ tools, loading }: Props) {
  if (loading) {
    return <div className="h-64 animate-pulse rounded bg-muted" />;
  }

  if (tools.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No tool usage data for this period.
      </div>
    );
  }

  const chartData = tools.slice(0, 15).map((t) => ({
    name: t.tool_name.length > 25 ? t.tool_name.slice(0, 22) + "..." : t.tool_name,
    fullName: t.tool_name,
    calls: t.call_count,
    avgMs: t.avg_duration_ms,
  }));

  return (
    <div className="space-y-6">
      {/* Bar chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20 }}>
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis
              dataKey="name"
              type="category"
              width={180}
              tick={{ fontSize: 11 }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="rounded-lg border bg-background p-3 shadow-md">
                    <p className="font-medium text-sm">{d.fullName}</p>
                    <p className="text-sm text-muted-foreground">{d.calls} calls</p>
                    <p className="text-sm text-muted-foreground">avg {d.avgMs.toFixed(0)}ms</p>
                  </div>
                );
              }}
            />
            <Bar dataKey="calls" radius={[0, 4, 4, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Table */}
      <div className="rounded-md border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="text-left p-2 font-medium">Tool</th>
              <th className="text-left p-2 font-medium">Agent</th>
              <th className="text-right p-2 font-medium">Calls</th>
              <th className="text-right p-2 font-medium">Avg Time</th>
              <th className="text-right p-2 font-medium">Success</th>
            </tr>
          </thead>
          <tbody>
            {tools.map((t) => (
              <tr key={t.tool_name} className="border-b last:border-0">
                <td className="p-2 font-mono text-xs">{t.tool_name}</td>
                <td className="p-2 text-xs text-muted-foreground">
                  {t.agent_name?.replace("Agent", "") || "-"}
                </td>
                <td className="p-2 text-right font-mono">{t.call_count}</td>
                <td className="p-2 text-right font-mono">{t.avg_duration_ms.toFixed(0)}ms</td>
                <td className="p-2 text-right">
                  <Badge
                    variant={t.success_rate >= 95 ? "secondary" : t.success_rate >= 80 ? "outline" : "destructive"}
                    className="text-xs"
                  >
                    {t.success_rate}%
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
