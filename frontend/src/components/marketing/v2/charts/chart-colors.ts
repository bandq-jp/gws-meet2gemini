/**
 * Chart color palette and utility functions
 */

export const CHART_COLORS = [
  "#3b82f6", // blue
  "#10b981", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // purple
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#f97316", // orange
  "#14b8a6", // teal
  "#a855f7", // violet
] as const;

export function getColor(index: number, explicit?: string): string {
  if (explicit) return explicit;
  return CHART_COLORS[index % CHART_COLORS.length];
}

export function formatNumber(value: unknown): string {
  if (typeof value !== "number") return String(value ?? "");
  if (Number.isInteger(value)) return value.toLocaleString("ja-JP");
  return value.toLocaleString("ja-JP", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}
