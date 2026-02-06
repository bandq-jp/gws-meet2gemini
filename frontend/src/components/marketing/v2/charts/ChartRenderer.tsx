"use client";

import { useRef, useState, useCallback } from "react";
import { Download, Check, Loader2 } from "lucide-react";
import { toPng } from "html-to-image";
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
  const chartRef = useRef<HTMLDivElement>(null);
  const [downloadState, setDownloadState] = useState<
    "idle" | "loading" | "done"
  >("idle");

  const handleDownload = useCallback(async () => {
    if (!chartRef.current || downloadState === "loading") return;

    setDownloadState("loading");
    try {
      const dataUrl = await toPng(chartRef.current, {
        backgroundColor: "#ffffff",
        pixelRatio: 2, // 2x for sharp output
        cacheBust: true,
      });

      // Trigger download
      const link = document.createElement("a");
      const filename = spec.title
        ? `${spec.title.replace(/[^a-zA-Z0-9\u3000-\u9fff]/g, "_")}.png`
        : `chart_${spec.type}.png`;
      link.download = filename;
      link.href = dataUrl;
      link.click();

      setDownloadState("done");
      setTimeout(() => setDownloadState("idle"), 2000);
    } catch (err) {
      console.error("[ChartRenderer] Failed to export image:", err);
      setDownloadState("idle");
    }
  }, [spec.title, spec.type, downloadState]);

  if (!Chart) {
    console.warn(`[ChartRenderer] Unknown chart type: ${spec.type}`);
    return null;
  }

  return (
    <div className="my-2 rounded-xl border border-[#e5e7eb] bg-white overflow-hidden group relative">
      {/* Download button - top-right corner */}
      <button
        onClick={handleDownload}
        disabled={downloadState === "loading"}
        className="absolute top-2 right-2 z-10 flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium bg-white/90 border border-[#e5e7eb] text-[#6b7280] hover:text-[#1a1a2e] hover:border-[#9ca3af] opacity-0 group-hover:opacity-100 transition-all duration-200 backdrop-blur-sm cursor-pointer disabled:cursor-wait"
        aria-label="画像としてダウンロード"
      >
        {downloadState === "loading" ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : downloadState === "done" ? (
          <>
            <Check className="w-3 h-3 text-[#10b981]" />
            <span className="text-[#10b981]">保存済み</span>
          </>
        ) : (
          <>
            <Download className="w-3 h-3" />
            <span className="hidden sm:inline">画像保存</span>
          </>
        )}
      </button>

      <div ref={chartRef}>
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
    </div>
  );
}
