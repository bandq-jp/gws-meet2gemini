"use client";

import type { ChartSpec } from "@/lib/marketing/types";
import { formatNumber } from "./chart-colors";

export function TableChartView({ spec }: { spec: ChartSpec }) {
  const { data, columns } = spec;
  if (!columns?.length) return null;

  return (
    <div className="overflow-x-auto rounded-lg border border-[#e5e7eb]">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="bg-[#f8f9fb] border-b border-[#e5e7eb]">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-3 py-2 font-semibold text-[#1a1a2e] whitespace-nowrap ${
                  col.align === "right"
                    ? "text-right"
                    : col.align === "center"
                      ? "text-center"
                      : "text-left"
                }`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, ri) => (
            <tr
              key={ri}
              className={ri % 2 === 0 ? "bg-white" : "bg-[#f8f9fb]/50"}
            >
              {columns.map((col) => {
                const val = row[col.key];
                const display =
                  typeof val === "number" ? formatNumber(val) : String(val ?? "");
                return (
                  <td
                    key={col.key}
                    className={`px-3 py-2 text-[#374151] whitespace-nowrap ${
                      col.align === "right"
                        ? "text-right tabular-nums"
                        : col.align === "center"
                          ? "text-center"
                          : "text-left"
                    }`}
                  >
                    {display}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
