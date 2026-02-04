"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { ChartSpec } from "@/lib/marketing/types";
import { getColor, formatNumber } from "./chart-colors";

export function LineChartView({ spec }: { spec: ChartSpec }) {
  const { data, xKey, yKeys } = spec;
  if (!xKey || !yKeys?.length) return null;

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => formatNumber(v)} />
        <Tooltip
          formatter={(value, name) => {
            const yKey = yKeys.find((yk) => yk.key === name);
            return [formatNumber(value), yKey?.label ?? String(name)];
          }}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
        />
        {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {yKeys.map((yk, i) => (
          <Line
            key={yk.key}
            type="monotone"
            dataKey={yk.key}
            name={yk.key}
            stroke={getColor(i, yk.color)}
            strokeWidth={2}
            dot={{ r: 2.5 }}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
