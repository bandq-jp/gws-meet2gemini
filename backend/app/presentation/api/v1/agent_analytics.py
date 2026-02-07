"""
Agent Analytics API - Observability dashboard endpoints for b&q Agent.

Provides:
- KPI overview (conversations, tool calls, error rate, tokens)
- Trace list with pagination
- Trace detail with span tree
- Tool usage statistics
- Agent routing statistics
- Token usage daily trends
- User usage statistics
- Error tracking
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.infrastructure.supabase.client import get_supabase
from .marketing_v2 import MarketingRequestContext, require_marketing_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent-analytics", tags=["agent-analytics"])


# ============================================================
# Enums & Models
# ============================================================

class PeriodFilter(str, Enum):
    today = "today"
    seven_days = "7d"
    thirty_days = "30d"
    all = "all"


def _period_to_start(period: PeriodFilter) -> datetime | None:
    """Convert period filter to start datetime."""
    now = datetime.now(timezone.utc)
    if period == PeriodFilter.today:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == PeriodFilter.seven_days:
        return now - timedelta(days=7)
    elif period == PeriodFilter.thirty_days:
        return now - timedelta(days=30)
    return None  # all


# ============================================================
# GET /overview
# ============================================================

@router.get("/overview")
async def get_overview(
    period: PeriodFilter = Query(PeriodFilter.seven_days),
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """KPI summary: conversations, tool calls, error rate, tokens, unique users."""
    sb = get_supabase()
    start = _period_to_start(period)

    try:
        query = sb.table("agent_traces").select(
            "id, status, duration_ms, total_llm_calls, total_tool_calls, "
            "total_input_tokens, total_output_tokens, user_email"
        )
        if start:
            query = query.gte("started_at", start.isoformat())

        result = query.execute()
        traces = result.data or []

        total = len(traces)
        errors = sum(1 for t in traces if t.get("status") == "error")
        unique_users = len({t.get("user_email") for t in traces if t.get("user_email")})
        total_llm = sum(t.get("total_llm_calls", 0) or 0 for t in traces)
        total_tools = sum(t.get("total_tool_calls", 0) or 0 for t in traces)
        total_in = sum(t.get("total_input_tokens", 0) or 0 for t in traces)
        total_out = sum(t.get("total_output_tokens", 0) or 0 for t in traces)
        durations = [t["duration_ms"] for t in traces if t.get("duration_ms")]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_conversations": total,
            "total_tool_calls": total_tools,
            "total_llm_calls": total_llm,
            "error_rate": round(errors / total * 100, 1) if total else 0,
            "error_count": errors,
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "unique_users": unique_users,
            "avg_duration_ms": round(avg_duration, 1),
        }
    except Exception as e:
        logger.exception(f"[Analytics] overview error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch overview")


# ============================================================
# GET /traces
# ============================================================

@router.get("/traces")
async def get_traces(
    period: PeriodFilter = Query(PeriodFilter.seven_days),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_email: str | None = Query(None),
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """Trace list with pagination."""
    sb = get_supabase()
    start = _period_to_start(period)

    try:
        query = sb.table("agent_traces").select(
            "id, trace_id, conversation_id, user_email, root_agent_name, "
            "started_at, ended_at, duration_ms, status, error_message, "
            "total_llm_calls, total_tool_calls, total_input_tokens, total_output_tokens, "
            "sub_agents_used, tools_used",
            count="exact",
        )
        if start:
            query = query.gte("started_at", start.isoformat())
        if user_email:
            query = query.eq("user_email", user_email)

        result = query.order("started_at", desc=True).range(offset, offset + limit - 1).execute()

        return {
            "traces": result.data or [],
            "total_count": result.count or 0,
        }
    except Exception as e:
        logger.exception(f"[Analytics] traces error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch traces")


# ============================================================
# GET /traces/{trace_id}
# ============================================================

@router.get("/traces/{trace_id}")
async def get_trace_detail(
    trace_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """Trace detail with full span tree."""
    sb = get_supabase()

    try:
        # Fetch trace
        trace_result = sb.table("agent_traces").select("*").eq("trace_id", trace_id).execute()
        if not trace_result.data:
            raise HTTPException(status_code=404, detail="Trace not found")

        trace = trace_result.data[0]

        # Fetch all spans for this trace
        spans_result = (
            sb.table("agent_spans")
            .select("*")
            .eq("trace_id", trace_id)
            .order("started_at", desc=False)
            .execute()
        )
        spans = spans_result.data or []

        # Build tree structure
        span_map: dict[str, dict] = {}
        roots: list[dict] = []

        for s in spans:
            s["children"] = []
            span_map[s["span_id"]] = s

        for s in spans:
            parent_id = s.get("parent_span_id")
            if parent_id and parent_id in span_map:
                span_map[parent_id]["children"].append(s)
            else:
                roots.append(s)

        return {
            "trace": trace,
            "spans": spans,
            "tree": roots,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Analytics] trace detail error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trace detail")


# ============================================================
# GET /tool-usage
# ============================================================

@router.get("/tool-usage")
async def get_tool_usage(
    period: PeriodFilter = Query(PeriodFilter.seven_days),
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """Tool usage statistics: frequency, avg duration, success rate."""
    sb = get_supabase()
    start = _period_to_start(period)

    try:
        query = sb.table("agent_spans").select(
            "tool_name, agent_name, duration_ms, status"
        ).eq("operation_name", "execute_tool").not_.is_("tool_name", "null")

        if start:
            query = query.gte("started_at", start.isoformat())

        result = query.execute()
        spans = result.data or []

        # Aggregate by tool_name
        tool_stats: dict[str, dict] = {}
        for s in spans:
            key = s["tool_name"]
            if key not in tool_stats:
                tool_stats[key] = {
                    "tool_name": key,
                    "agent_name": s.get("agent_name"),
                    "call_count": 0,
                    "total_duration": 0,
                    "ok_count": 0,
                    "error_count": 0,
                }
            stats = tool_stats[key]
            stats["call_count"] += 1
            if s.get("duration_ms"):
                stats["total_duration"] += s["duration_ms"]
            if s.get("status") == "ok":
                stats["ok_count"] += 1
            else:
                stats["error_count"] += 1

        tools = []
        for stats in sorted(tool_stats.values(), key=lambda x: x["call_count"], reverse=True):
            tools.append({
                "tool_name": stats["tool_name"],
                "agent_name": stats["agent_name"],
                "call_count": stats["call_count"],
                "avg_duration_ms": round(stats["total_duration"] / stats["call_count"], 1) if stats["call_count"] else 0,
                "success_rate": round(stats["ok_count"] / stats["call_count"] * 100, 1) if stats["call_count"] else 0,
                "error_count": stats["error_count"],
            })

        return {"tools": tools}
    except Exception as e:
        logger.exception(f"[Analytics] tool-usage error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tool usage")


# ============================================================
# GET /agent-routing
# ============================================================

@router.get("/agent-routing")
async def get_agent_routing(
    period: PeriodFilter = Query(PeriodFilter.seven_days),
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """Agent routing statistics: which sub-agents are selected and how often."""
    sb = get_supabase()
    start = _period_to_start(period)

    try:
        query = sb.table("agent_traces").select(
            "sub_agents_used, total_tool_calls"
        )
        if start:
            query = query.gte("started_at", start.isoformat())

        result = query.execute()
        traces = result.data or []

        agent_counts: dict[str, dict] = {}
        for t in traces:
            agents = t.get("sub_agents_used") or []
            tool_calls = t.get("total_tool_calls", 0) or 0
            for agent in agents:
                if agent not in agent_counts:
                    agent_counts[agent] = {"call_count": 0, "total_tools": 0}
                agent_counts[agent]["call_count"] += 1
                # Approximate: distribute tools evenly among agents
                if agents:
                    agent_counts[agent]["total_tools"] += tool_calls / len(agents)

        agents = []
        for name, stats in sorted(agent_counts.items(), key=lambda x: x[1]["call_count"], reverse=True):
            agents.append({
                "agent_name": name,
                "call_count": stats["call_count"],
                "avg_tools_per_call": round(stats["total_tools"] / stats["call_count"], 1) if stats["call_count"] else 0,
            })

        return {"agents": agents}
    except Exception as e:
        logger.exception(f"[Analytics] agent-routing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch agent routing")


# ============================================================
# GET /token-usage
# ============================================================

@router.get("/token-usage")
async def get_token_usage(
    period: PeriodFilter = Query(PeriodFilter.thirty_days),
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """Token usage daily trends with cost estimation."""
    sb = get_supabase()
    start = _period_to_start(period)

    try:
        query = sb.table("agent_traces").select(
            "started_at, total_input_tokens, total_output_tokens"
        )
        if start:
            query = query.gte("started_at", start.isoformat())

        result = query.order("started_at", desc=False).execute()
        traces = result.data or []

        # Aggregate by day
        daily: dict[str, dict] = {}
        for t in traces:
            if not t.get("started_at"):
                continue
            day = t["started_at"][:10]  # YYYY-MM-DD
            if day not in daily:
                daily[day] = {"input_tokens": 0, "output_tokens": 0, "trace_count": 0}
            daily[day]["input_tokens"] += t.get("total_input_tokens", 0) or 0
            daily[day]["output_tokens"] += t.get("total_output_tokens", 0) or 0
            daily[day]["trace_count"] += 1

        # Gemini 3 Flash pricing: $0.50/1M input, $3.00/1M output
        result_daily = []
        for day in sorted(daily.keys()):
            d = daily[day]
            cost = (d["input_tokens"] / 1_000_000 * 0.50) + (d["output_tokens"] / 1_000_000 * 3.00)
            result_daily.append({
                "day": day,
                "input_tokens": d["input_tokens"],
                "output_tokens": d["output_tokens"],
                "trace_count": d["trace_count"],
                "estimated_cost_usd": round(cost, 4),
            })

        return {"daily": result_daily}
    except Exception as e:
        logger.exception(f"[Analytics] token-usage error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch token usage")


# ============================================================
# GET /user-usage
# ============================================================

@router.get("/user-usage")
async def get_user_usage(
    period: PeriodFilter = Query(PeriodFilter.thirty_days),
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """User usage statistics."""
    sb = get_supabase()
    start = _period_to_start(period)

    try:
        query = sb.table("agent_traces").select(
            "user_email, started_at, total_input_tokens, total_output_tokens"
        )
        if start:
            query = query.gte("started_at", start.isoformat())

        result = query.execute()
        traces = result.data or []

        user_stats: dict[str, dict] = {}
        for t in traces:
            email = t.get("user_email") or "unknown"
            if email not in user_stats:
                user_stats[email] = {
                    "trace_count": 0,
                    "last_used": "",
                    "total_tokens": 0,
                }
            user_stats[email]["trace_count"] += 1
            started = t.get("started_at", "")
            if started > user_stats[email]["last_used"]:
                user_stats[email]["last_used"] = started
            user_stats[email]["total_tokens"] += (
                (t.get("total_input_tokens", 0) or 0) +
                (t.get("total_output_tokens", 0) or 0)
            )

        users = []
        for email, stats in sorted(user_stats.items(), key=lambda x: x[1]["trace_count"], reverse=True):
            users.append({
                "user_email": email,
                "trace_count": stats["trace_count"],
                "last_used": stats["last_used"],
                "total_tokens": stats["total_tokens"],
            })

        return {"users": users}
    except Exception as e:
        logger.exception(f"[Analytics] user-usage error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user usage")


# ============================================================
# GET /errors
# ============================================================

@router.get("/errors")
async def get_errors(
    period: PeriodFilter = Query(PeriodFilter.seven_days),
    limit: int = Query(50, ge=1, le=200),
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """Error tracking list."""
    sb = get_supabase()
    start = _period_to_start(period)

    try:
        query = (
            sb.table("agent_spans")
            .select("trace_id, span_id, agent_name, tool_name, error_message, started_at, operation_name")
            .eq("status", "error")
        )
        if start:
            query = query.gte("started_at", start.isoformat())

        result = query.order("started_at", desc=True).limit(limit).execute()

        return {"errors": result.data or []}
    except Exception as e:
        logger.exception(f"[Analytics] errors error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch errors")
