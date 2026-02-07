"use client";

import type { UserUsageStat } from "@/lib/operations/types";

interface Props {
  users: UserUsageStat[];
  loading: boolean;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatTime(iso: string): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function UserUsageTable({ users, loading }: Props) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-10 animate-pulse rounded bg-muted" />
        ))}
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No user data for this period.
      </div>
    );
  }

  return (
    <div className="rounded-md border overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="text-left p-3 font-medium">User</th>
            <th className="text-right p-3 font-medium">Conversations</th>
            <th className="text-right p-3 font-medium">Total Tokens</th>
            <th className="text-right p-3 font-medium">Last Active</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.user_email} className="border-b last:border-0">
              <td className="p-3">{u.user_email}</td>
              <td className="p-3 text-right font-mono">{u.trace_count}</td>
              <td className="p-3 text-right font-mono">{formatTokens(u.total_tokens)}</td>
              <td className="p-3 text-right text-muted-foreground text-xs">
                {formatTime(u.last_used)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
