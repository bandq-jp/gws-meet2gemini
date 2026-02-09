"use client";

/**
 * AgentShowcase - Agent capability showcase dialog
 *
 * Shows all 11 agents, their tools, connected services, and sample queries.
 * Pure CSS transitions — no animation library dependency.
 *
 * Design: Monochromatic brand teal (#1e8aa0) + neutral grays.
 * No per-agent color coding — clean, editorial, professional.
 */

import { useState, useMemo } from "react";
import { X, ChevronDown, Wrench, Layers, ArrowRight } from "lucide-react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  AGENTS,
  AGENT_CATEGORIES,
  type AgentCategory,
  type AgentInfo,
} from "./agent-showcase-data";

// ---------------------------------------------------------------------------
// ToolList (expanded detail)
// ---------------------------------------------------------------------------

function ToolList({ agent }: { agent: AgentInfo }) {
  const sections = agent.tiers?.length
    ? agent.tiers
    : agent.tools.length
      ? [{ name: "", tools: agent.tools }]
      : [];

  if (sections.length === 0) return null;

  return (
    <div className="px-4 pb-4 pt-1">
      <div className="border-t border-dashed border-[#e5e7eb] pt-3 mb-2">
        <span className="text-[10px] font-semibold tracking-widest uppercase text-[#9ca3af]">
          ツール一覧
        </span>
        <span className="text-[10px] text-[#c5c8ce] ml-1.5">
          ({agent.toolCount})
        </span>
      </div>
      <div className="max-h-[220px] overflow-y-auto pr-1 space-y-2.5 custom-scrollbar">
        {sections.map((section) => (
          <div key={section.name || "flat"}>
            {section.name && (
              <div className="text-[9px] font-bold uppercase tracking-[0.08em] mb-1.5 pl-0.5 text-[#1e8aa0]/50">
                {section.name}
              </div>
            )}
            <div className="space-y-0.5">
              {section.tools.map((tool) => (
                <div
                  key={tool.name}
                  className="flex items-center gap-2 py-[5px] px-2 rounded-md hover:bg-[#f8f9fb] transition-colors"
                >
                  <Wrench className="w-3 h-3 shrink-0 text-[#d0d3d9]" />
                  <span className="text-[11px] text-[#4b5563] leading-tight">
                    {tool.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AgentCard
// ---------------------------------------------------------------------------

function AgentCard({
  agent,
  visible = true,
  onTryQuery,
}: {
  agent: AgentInfo;
  visible?: boolean;
  onTryQuery?: (query: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const Icon = agent.icon;

  if (!visible) return null;

  return (
    <div
      className={cn(
        "relative rounded-xl border border-[#e8eaef] bg-background overflow-hidden",
        "transition-all duration-200",
        "hover:shadow-lg hover:shadow-black/[0.04] hover:-translate-y-0.5",
        "hover:border-[#1e8aa0]/20",
      )}
    >
      {/* Thin accent line — uniform brand teal */}
      <div className="h-[2px] bg-[#1e8aa0]/15" />

      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 bg-[#1e8aa0]/[0.06]">
              <Icon
                className="w-[18px] h-[18px] text-[#1e8aa0]"
                strokeWidth={1.75}
              />
            </div>
            <div>
              <h3 className="text-[13.5px] font-semibold text-foreground leading-tight">
                {agent.displayName}
              </h3>
              <p className="text-[11px] text-muted-foreground/60 mt-0.5 leading-tight">
                {agent.tagline}
              </p>
            </div>
          </div>
          <span className="text-[10px] font-semibold px-2 py-[3px] rounded-full shrink-0 bg-[#f0f1f5] text-[#6b7280]">
            {agent.isMcp ? "~" : ""}
            {agent.toolCount} tools
          </span>
        </div>

        {/* Description */}
        <p className="text-[12px] text-[#6b7280] leading-[1.65] mb-3">
          {agent.description}
        </p>

        {/* Service badges */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {agent.services.map((s) => (
            <span
              key={s}
              className="text-[10px] px-2 py-[3px] rounded-full bg-[#f0f1f5] text-[#6b7280] font-medium"
            >
              {s}
            </span>
          ))}
        </div>

        {/* Highlights */}
        <div className="space-y-1.5 mb-3">
          {agent.highlights.map((h, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="w-[5px] h-[5px] rounded-full mt-[5px] shrink-0 bg-[#1e8aa0]/30" />
              <span className="text-[11px] text-[#6b7280] leading-relaxed">
                {h}
              </span>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2 pt-3 border-t border-[#f0f1f5]">
          <button
            onClick={() => onTryQuery?.(agent.exampleQuery)}
            className="group flex-1 min-w-0 text-left flex items-center gap-1"
          >
            <span className="text-[10.5px] text-[#b0b5c0] truncate group-hover:text-[#1e8aa0] transition-colors">
              &ldquo;{agent.exampleQuery.slice(0, 38)}...&rdquo;
            </span>
            <ArrowRight className="w-3 h-3 shrink-0 text-[#d0d3d9] group-hover:text-[#1e8aa0] group-hover:translate-x-0.5 transition-all" />
          </button>

          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[11px] sm:text-[10px] font-medium text-[#9ca3af] hover:text-[#6b7280] transition-colors flex items-center gap-0.5 shrink-0 py-2 px-2.5 sm:py-1 sm:px-1.5 -mr-1.5 rounded-md hover:bg-[#f8f9fb]"
          >
            {expanded ? "閉じる" : "詳細"}
            <ChevronDown
              className={cn(
                "w-3 h-3 transition-transform duration-200",
                expanded && "rotate-180",
              )}
            />
          </button>
        </div>
      </div>

      {/* Expandable tool list — CSS grid transition for height */}
      <div
        className={cn(
          "grid transition-[grid-template-rows] duration-200 ease-out",
          expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="overflow-hidden">
          <ToolList agent={agent} />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StatPill
// ---------------------------------------------------------------------------

function StatPill({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px] bg-[#1e8aa0]/[0.06] rounded-full px-2.5 py-1">
      <span className="font-bold text-[#1e8aa0]">{value}</span>
      <span className="text-[#6b7280]">{label}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Showcase
// ---------------------------------------------------------------------------

export interface AgentShowcaseProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTryQuery?: (query: string) => void;
}

export function AgentShowcase({
  open,
  onOpenChange,
  onTryQuery,
}: AgentShowcaseProps) {
  const [activeCategory, setActiveCategory] = useState<
    AgentCategory | "all"
  >("all");

  const totalTools = useMemo(
    () => AGENTS.reduce((sum, a) => sum + a.toolCount, 0),
    [],
  );

  const categories = [
    { key: "all" as const, label: "全て" },
    ...Object.entries(AGENT_CATEGORIES).map(([key, val]) => ({
      key: key as AgentCategory,
      label: val.label,
    })),
  ];

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        {/* Overlay */}
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0 duration-200"
        />

        {/* Content */}
        <DialogPrimitive.Content
          className={cn(
            "fixed z-50 flex flex-col bg-background border shadow-2xl shadow-black/10 outline-none overflow-hidden",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0",
            "data-[state=open]:zoom-in-[0.97] data-[state=closed]:zoom-out-[0.97]",
            "data-[state=open]:slide-in-from-bottom-4 data-[state=closed]:slide-out-to-bottom-2",
            "duration-200",
            // Desktop
            "sm:top-[50%] sm:left-[50%] sm:translate-x-[-50%] sm:translate-y-[-50%]",
            "sm:max-w-5xl sm:w-[calc(100%-3rem)] sm:h-[85vh] sm:rounded-2xl",
            // Mobile
            "max-sm:inset-x-0 max-sm:bottom-0 max-sm:top-auto",
            "max-sm:rounded-t-2xl max-sm:rounded-b-none",
            "max-sm:h-[92dvh] max-sm:max-w-full",
          )}
        >
          {/* Header */}
          <div className="shrink-0 px-5 sm:px-6 pt-5 pb-3">
            <div className="sm:hidden flex justify-center mb-3">
              <div className="w-8 h-1 rounded-full bg-[#e5e7eb]" />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#1e8aa0]/[0.08] flex items-center justify-center">
                  <Layers
                    className="w-[18px] h-[18px] text-[#1e8aa0]"
                    strokeWidth={1.5}
                  />
                </div>
                <div>
                  <DialogPrimitive.Title className="text-[15px] font-semibold text-foreground tracking-tight">
                    エージェント一覧
                  </DialogPrimitive.Title>
                  <DialogPrimitive.Description className="sr-only">
                    b&qエージェントに搭載された11のAIエージェントとツールの詳細一覧
                  </DialogPrimitive.Description>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="hidden sm:flex items-center gap-1.5">
                  <StatPill value={`${AGENTS.length}`} label="agents" />
                  <StatPill value={`${totalTools}+`} label="tools" />
                </div>
                <button
                  onClick={() => onOpenChange(false)}
                  className="w-10 h-10 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center text-[#c5c8ce] hover:text-foreground hover:bg-[#f0f1f5] transition-colors ml-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="sm:hidden flex items-center gap-1.5 mt-3">
              <StatPill value={`${AGENTS.length}`} label="agents" />
              <StatPill value={`${totalTools}+`} label="tools" />
            </div>
          </div>

          {/* Category filter */}
          <div className="shrink-0 px-5 sm:px-6 pb-3">
            <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-0.5">
              {categories.map((cat) => (
                <button
                  key={cat.key}
                  onClick={() => setActiveCategory(cat.key)}
                  className={cn(
                    "px-3.5 py-2 sm:px-3 sm:py-1.5 rounded-full text-[11px] font-medium whitespace-nowrap transition-all duration-200",
                    activeCategory === cat.key
                      ? "bg-[#1e8aa0] text-white shadow-sm shadow-[#1e8aa0]/20"
                      : "bg-[#f0f1f5] text-[#6b7280] hover:bg-[#e5e7eb] hover:text-[#374151]",
                  )}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          <Separator />

          {/* Card grid */}
          <div className="flex-1 min-h-0 overflow-y-auto">
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 p-4 sm:p-6">
              {AGENTS.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  visible={
                    activeCategory === "all" ||
                    agent.category === activeCategory
                  }
                  onTryQuery={(q) => {
                    onTryQuery?.(q);
                    onOpenChange(false);
                  }}
                />
              ))}
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
