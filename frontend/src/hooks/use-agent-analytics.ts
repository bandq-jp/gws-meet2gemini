"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  PeriodFilter,
  AnalyticsOverview,
  TraceOverview,
  TraceDetailResponse,
  ToolUsageStat,
  AgentRoutingStat,
  TokenUsageDaily,
  UserUsageStat,
  AgentError,
} from "@/lib/operations/types";

const API_BASE = "/api/marketing-v2/chatkit/start";
const ANALYTICS_BASE = "/api/v1/agent-analytics";

async function getToken(): Promise<string> {
  const res = await fetch(API_BASE, { method: "POST" });
  if (!res.ok) throw new Error("Failed to get token");
  const data = await res.json();
  return data.client_secret || data.token || "";
}

let _cachedToken: string | null = null;

async function fetchAnalytics<T>(path: string, params?: Record<string, string>): Promise<T> {
  if (!_cachedToken) {
    _cachedToken = await getToken();
  }

  const url = new URL(path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, v);
    });
  }

  const res = await fetch(url.toString(), {
    headers: { "x-marketing-client-secret": _cachedToken },
    cache: "no-store",
  });

  if (res.status === 401) {
    // Token expired, retry once
    _cachedToken = await getToken();
    const retry = await fetch(url.toString(), {
      headers: { "x-marketing-client-secret": _cachedToken },
      cache: "no-store",
    });
    if (!retry.ok) throw new Error(`API error: ${retry.status}`);
    return retry.json();
  }

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ============================================================
// Hooks
// ============================================================

export function useAnalyticsOverview(period: PeriodFilter) {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAnalytics<AnalyticsOverview>(
        `${ANALYTICS_BASE}/overview`,
        { period }
      );
      setData(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, reload: load };
}

export function useTraceList(period: PeriodFilter, limit = 50, offset = 0) {
  const [traces, setTraces] = useState<TraceOverview[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAnalytics<{ traces: TraceOverview[]; total_count: number }>(
        `${ANALYTICS_BASE}/traces`,
        { period, limit: String(limit), offset: String(offset) }
      );
      setTraces(result.traces);
      setTotalCount(result.total_count);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [period, limit, offset]);

  useEffect(() => { load(); }, [load]);

  return { traces, totalCount, loading, error, reload: load };
}

export function useTraceDetail(traceId: string | null) {
  const [data, setData] = useState<TraceDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!traceId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAnalytics<TraceDetailResponse>(
        `${ANALYTICS_BASE}/traces/${traceId}`
      );
      setData(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [traceId]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error };
}

export function useToolUsage(period: PeriodFilter) {
  const [tools, setTools] = useState<ToolUsageStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchAnalytics<{ tools: ToolUsageStat[] }>(
        `${ANALYTICS_BASE}/tool-usage`,
        { period }
      );
      setTools(result.tools);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => { load(); }, [load]);

  return { tools, loading, error };
}

export function useAgentRouting(period: PeriodFilter) {
  const [agents, setAgents] = useState<AgentRoutingStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchAnalytics<{ agents: AgentRoutingStat[] }>(
        `${ANALYTICS_BASE}/agent-routing`,
        { period }
      );
      setAgents(result.agents);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => { load(); }, [load]);

  return { agents, loading, error };
}

export function useTokenUsage(period: PeriodFilter) {
  const [daily, setDaily] = useState<TokenUsageDaily[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchAnalytics<{ daily: TokenUsageDaily[] }>(
        `${ANALYTICS_BASE}/token-usage`,
        { period }
      );
      setDaily(result.daily);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => { load(); }, [load]);

  return { daily, loading, error };
}

export function useUserUsage(period: PeriodFilter) {
  const [users, setUsers] = useState<UserUsageStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchAnalytics<{ users: UserUsageStat[] }>(
        `${ANALYTICS_BASE}/user-usage`,
        { period }
      );
      setUsers(result.users);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => { load(); }, [load]);

  return { users, loading, error };
}

export function useErrorList(period: PeriodFilter, limit = 50) {
  const [errors, setErrors] = useState<AgentError[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchAnalytics<{ errors: AgentError[] }>(
        `${ANALYTICS_BASE}/errors`,
        { period, limit: String(limit) }
      );
      setErrors(result.errors);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [period, limit]);

  useEffect(() => { load(); }, [load]);

  return { errors: errors, loading, error };
}
