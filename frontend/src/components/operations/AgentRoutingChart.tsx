"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import type { PieLabelRenderProps } from "recharts";
import type { AgentRoutingStat } from "@/lib/operations/types";

interface Props {
  agents: AgentRoutingStat[];
  loading: boolean;
}

const COLORS = [
  "#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444",
  "#ec4899", "#6366f1", "#14b8a6", "#f97316", "#84cc16",
];

export function AgentRoutingChart({ agents, loading }: Props) {
  if (loading) {
    return <div className="h-64 animate-pulse rounded bg-muted" />;
  }

  if (agents.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No agent routing data for this period.
      </div>
    );
  }

  const pieData = agents.map((a, i) => ({
    name: a.agent_name.replace("Agent", ""),
    value: a.call_count,
    fill: COLORS[i % COLORS.length],
  }));

  const barData = agents.map((a) => ({
    name: a.agent_name.replace("Agent", ""),
    calls: a.call_count,
    tools: a.avg_tools_per_call,
  }));

  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Pie chart */}
      <div>
        <h4 className="text-sm font-medium mb-2">Routing Distribution</h4>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
                label={(props: PieLabelRenderProps) =>
                  `${props.name ?? ""} ${(((props.percent as number) ?? 0) * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="rounded-lg border bg-background p-2 shadow-md text-sm">
                      <p className="font-medium">{d.name}</p>
                      <p className="text-muted-foreground">{d.value} calls</p>
                    </div>
                  );
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bar chart: calls + avg tools */}
      <div>
        <h4 className="text-sm font-medium mb-2">Calls & Avg Tools per Call</h4>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="rounded-lg border bg-background p-2 shadow-md text-sm">
                      <p className="font-medium">{d.name}</p>
                      <p className="text-muted-foreground">{d.calls} routing calls</p>
                      <p className="text-muted-foreground">{d.tools} avg tools/call</p>
                    </div>
                  );
                }}
              />
              <Bar dataKey="calls" radius={[4, 4, 0, 0]}>
                {barData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
