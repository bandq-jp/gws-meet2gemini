"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from "recharts";
import type { ChartSpec } from "@/lib/marketing/types";
import { CHART_COLORS, formatNumber } from "./chart-colors";

export function FunnelChartView({ spec }: { spec: ChartSpec }) {
  const { data, nameField, valueField } = spec;
  if (!nameField || !valueField) return null;

  // Sort by value descending for funnel effect
  const sorted = [...data].sort(
    (a, b) => (Number(b[valueField]) || 0) - (Number(a[valueField]) || 0)
  );

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={sorted} layout="vertical" margin={{ top: 5, right: 10, left: 80, bottom: 5 }}>
        <XAxis type="number" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => formatNumber(v)} />
        <YAxis type="category" dataKey={nameField} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={75} />
        <Tooltip
          formatter={(value) => [formatNumber(value), ""]}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
        />
        <Bar dataKey={valueField} radius={[0, 4, 4, 0]}>
          {sorted.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
