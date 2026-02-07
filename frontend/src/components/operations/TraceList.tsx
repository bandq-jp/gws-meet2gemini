"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ExternalLink, ChevronLeft, ChevronRight } from "lucide-react";
import type { TraceOverview } from "@/lib/operations/types";

interface Props {
  traces: TraceOverview[];
  totalCount: number;
  loading: boolean;
  offset: number;
  limit: number;
  onPageChange: (newOffset: number) => void;
  onSelectTrace: (traceId: string) => void;
  phoenixUrl?: string;
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "-";
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`;
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const AGENT_COLORS: Record<string, string> = {
  ZohoCRMAgent: "bg-emerald-100 text-emerald-800",
  SEOAnalysisAgent: "bg-sky-100 text-sky-800",
  CompanyDatabaseAgent: "bg-indigo-100 text-indigo-800",
  CASupportAgent: "bg-rose-100 text-rose-800",
  CandidateInsightAgent: "bg-orange-100 text-orange-800",
  GoogleSearchAgent: "bg-blue-100 text-blue-800",
  CodeExecutionAgent: "bg-gray-100 text-gray-800",
  WorkspaceAgent: "bg-red-100 text-red-800",
  SlackAgent: "bg-fuchsia-100 text-fuchsia-800",
};

export function TraceList({
  traces,
  totalCount,
  loading,
  offset,
  limit,
  onPageChange,
  onSelectTrace,
  phoenixUrl,
}: Props) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 animate-pulse rounded bg-muted" />
        ))}
      </div>
    );
  }

  if (traces.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No traces found for this period.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[140px]">Time</TableHead>
              <TableHead>User</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Agents</TableHead>
              <TableHead className="text-right">Tools</TableHead>
              <TableHead className="text-right">Tokens</TableHead>
              <TableHead>Status</TableHead>
              {phoenixUrl && <TableHead className="w-[40px]" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {traces.map((t) => (
              <TableRow
                key={t.trace_id}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => onSelectTrace(t.trace_id)}
              >
                <TableCell className="text-xs font-mono">
                  {formatTime(t.started_at)}
                </TableCell>
                <TableCell className="text-sm">
                  {t.user_email?.split("@")[0] || "-"}
                </TableCell>
                <TableCell className="text-sm font-mono">
                  {formatDuration(t.duration_ms)}
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {(t.sub_agents_used || []).slice(0, 3).map((a) => (
                      <Badge
                        key={a}
                        variant="secondary"
                        className={`text-xs ${AGENT_COLORS[a] || "bg-gray-100 text-gray-800"}`}
                      >
                        {a.replace("Agent", "")}
                      </Badge>
                    ))}
                    {(t.sub_agents_used || []).length > 3 && (
                      <Badge variant="secondary" className="text-xs">
                        +{t.sub_agents_used.length - 3}
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right text-sm font-mono">
                  {t.total_tool_calls}
                </TableCell>
                <TableCell className="text-right text-sm font-mono">
                  {((t.total_input_tokens + t.total_output_tokens) / 1000).toFixed(1)}K
                </TableCell>
                <TableCell>
                  <Badge variant={t.status === "ok" ? "secondary" : "destructive"} className="text-xs">
                    {t.status}
                  </Badge>
                </TableCell>
                {phoenixUrl && (
                  <TableCell>
                    <a
                      href={`${phoenixUrl}/tracing/traces/${t.trace_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      title="Open in Phoenix"
                    >
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
                    </a>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          {offset + 1}-{Math.min(offset + limit, totalCount)} of {totalCount}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={offset === 0}
            onClick={() => onPageChange(Math.max(0, offset - limit))}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={offset + limit >= totalCount}
            onClick={() => onPageChange(offset + limit)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
