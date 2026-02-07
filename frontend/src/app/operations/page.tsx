"use client";

import { useState } from "react";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ExternalLink, Activity, RefreshCw } from "lucide-react";
import type { PeriodFilter } from "@/lib/operations/types";
import {
  useAnalyticsOverview,
  useTraceList,
  useToolUsage,
  useAgentRouting,
  useTokenUsage,
  useUserUsage,
  useErrorList,
} from "@/hooks/use-agent-analytics";
import { PeriodFilterToggle } from "@/components/operations/PeriodFilter";
import { OverviewCards } from "@/components/operations/OverviewCards";
import { TraceList } from "@/components/operations/TraceList";
import { TraceDetail } from "@/components/operations/TraceDetail";
import { ToolUsageChart } from "@/components/operations/ToolUsageChart";
import { AgentRoutingChart } from "@/components/operations/AgentRoutingChart";
import { TokenUsageChart } from "@/components/operations/TokenUsageChart";
import { UserUsageTable } from "@/components/operations/UserUsageTable";
import { ErrorList } from "@/components/operations/ErrorList";

const PHOENIX_URL = process.env.NEXT_PUBLIC_PHOENIX_URL || "http://localhost:6006";

export default function OperationsPage() {
  const [period, setPeriod] = useState<PeriodFilter>("7d");
  const [traceOffset, setTraceOffset] = useState(0);
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null);
  const TRACE_LIMIT = 30;

  // Data hooks
  const overview = useAnalyticsOverview(period);
  const traceList = useTraceList(period, TRACE_LIMIT, traceOffset);
  const toolUsage = useToolUsage(period);
  const agentRouting = useAgentRouting(period);
  const tokenUsage = useTokenUsage(period);
  const userUsage = useUserUsage(period);
  const errorList = useErrorList(period);

  const handleReload = () => {
    overview.reload();
    traceList.reload();
  };

  return (
    <div className="container mx-auto px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <SidebarTrigger className="md:hidden" />
          <div className="rounded-lg bg-gradient-to-br from-violet-500/10 to-blue-500/10 p-2">
            <Activity className="h-6 w-6 text-violet-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              b&q Agent Analytics
            </h1>
            <p className="text-sm text-muted-foreground">
              ADK Orchestrator traces, tools, tokens, routing
            </p>
          </div>
          <Badge variant="secondary" className="ml-2">
            Phoenix + OTel
          </Badge>
        </div>

        <div className="flex items-center gap-3">
          <PeriodFilterToggle value={period} onChange={(v) => { setPeriod(v); setTraceOffset(0); }} />
          <Button variant="outline" size="sm" onClick={handleReload}>
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
            Reload
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={PHOENIX_URL} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
              Phoenix UI
            </a>
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <OverviewCards data={overview.data} loading={overview.loading} />

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="traces">
            Traces
            {traceList.totalCount > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-xs">
                {traceList.totalCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="tools">Tools</TabsTrigger>
          <TabsTrigger value="tokens">Tokens</TabsTrigger>
          <TabsTrigger value="errors">
            Errors
            {overview.data && overview.data.error_count > 0 && (
              <Badge variant="destructive" className="ml-1.5 text-xs">
                {overview.data.error_count}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium mb-3">Agent Routing</h3>
              <AgentRoutingChart agents={agentRouting.agents} loading={agentRouting.loading} />
            </div>
            <div>
              <h3 className="text-sm font-medium mb-3">Token Usage (30d)</h3>
              <TokenUsageChart daily={tokenUsage.daily} loading={tokenUsage.loading} />
            </div>
          </div>
          <div>
            <h3 className="text-sm font-medium mb-3">Users</h3>
            <UserUsageTable users={userUsage.users} loading={userUsage.loading} />
          </div>
        </TabsContent>

        {/* Traces Tab */}
        <TabsContent value="traces">
          <TraceList
            traces={traceList.traces}
            totalCount={traceList.totalCount}
            loading={traceList.loading}
            offset={traceOffset}
            limit={TRACE_LIMIT}
            onPageChange={setTraceOffset}
            onSelectTrace={setSelectedTrace}
            phoenixUrl={PHOENIX_URL}
          />
        </TabsContent>

        {/* Tools Tab */}
        <TabsContent value="tools">
          <ToolUsageChart tools={toolUsage.tools} loading={toolUsage.loading} />
        </TabsContent>

        {/* Tokens Tab */}
        <TabsContent value="tokens">
          <TokenUsageChart daily={tokenUsage.daily} loading={tokenUsage.loading} />
        </TabsContent>

        {/* Errors Tab */}
        <TabsContent value="errors">
          <ErrorList
            errors={errorList.errors}
            loading={errorList.loading}
            onSelectTrace={setSelectedTrace}
          />
        </TabsContent>
      </Tabs>

      {/* Trace Detail Sheet */}
      <TraceDetail
        traceId={selectedTrace}
        onClose={() => setSelectedTrace(null)}
        phoenixUrl={PHOENIX_URL}
      />
    </div>
  );
}
