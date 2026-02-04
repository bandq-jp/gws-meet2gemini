"use client";

import type { ChartSpec } from "@/lib/marketing/types";
import { LineChartView } from "./LineChartView";
import { BarChartView } from "./BarChartView";
import { AreaChartView } from "./AreaChartView";
import { PieChartView } from "./PieChartView";
import { RadarChartView } from "./RadarChartView";
import { FunnelChartView } from "./FunnelChartView";
import { TableChartView } from "./TableChartView";

const CHART_MAP: Record<
  ChartSpec["type"],
  React.ComponentType<{ spec: ChartSpec }>
> = {
  line: LineChartView,
  bar: BarChartView,
  area: AreaChartView,
  pie: PieChartView,
  donut: PieChartView,
  scatter: LineChartView, // Fallback to line for scatter
  radar: RadarChartView,
  funnel: FunnelChartView,
  table: TableChartView,
};

export function ChartRenderer({ spec }: { spec: ChartSpec }) {
  const Chart = CHART_MAP[spec.type];
  if (!Chart) {
    console.warn(`[ChartRenderer] Unknown chart type: ${spec.type}`);
    return null;
  }

  return (
    <div className="my-2 rounded-xl border border-[#e5e7eb] bg-white overflow-hidden">
      {spec.title && (
        <div className="px-4 pt-3 pb-1">
          <h4 className="text-sm font-semibold text-[#1a1a2e]">
            {spec.title}
          </h4>
          {spec.description && (
            <p className="text-xs text-[#9ca3af] mt-0.5">
              {spec.description}
            </p>
          )}
        </div>
      )}
      <div className="px-2 pb-3">
        <Chart spec={spec} />
      </div>
    </div>
  );
}
