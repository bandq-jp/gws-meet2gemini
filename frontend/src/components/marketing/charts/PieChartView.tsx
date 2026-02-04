"use client";

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { ChartSpec } from "@/lib/marketing/types";
import { CHART_COLORS, formatNumber } from "./chart-colors";

export function PieChartView({ spec }: { spec: ChartSpec }) {
  const { data, nameKey, valueKey, type } = spec;
  if (!nameKey || !valueKey) return null;

  const isDonut = type === "donut";

  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={nameKey}
          cx="50%"
          cy="50%"
          innerRadius={isDonut ? "45%" : 0}
          outerRadius="75%"
          paddingAngle={2}
          label={({ name, percent }) =>
            `${name} ${((percent ?? 0) * 100).toFixed(1)}%`
          }
          labelLine={{ strokeWidth: 1 }}
          fontSize={11}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => [formatNumber(value), ""]}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
