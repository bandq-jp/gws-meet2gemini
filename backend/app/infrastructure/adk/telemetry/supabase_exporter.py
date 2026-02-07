"""
Custom OpenTelemetry SpanExporter that writes ADK spans to Supabase.

Captures:
- agent_traces: root invocation spans (one per conversation turn)
- agent_spans: all individual spans (invoke_agent, call_llm, execute_tool, send_data)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Sequence

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan

logger = logging.getLogger(__name__)

# ADK OTel attribute keys
_OP_NAME = "gen_ai.operation.name"
_AGENT_NAME = "gen_ai.agent.name"
_TOOL_NAME = "gen_ai.tool.name"
_MODEL = "gen_ai.request.model"
_INPUT_TOKENS = "gen_ai.usage.input_tokens"
_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
_FINISH_REASONS = "gen_ai.response.finish_reasons"
_CONVERSATION_ID = "gen_ai.conversation.id"
_SESSION_ID = "gcp.vertex.agent.session_id"


def _ns_to_datetime(ns: int | None) -> datetime | None:
    """Convert OTel nanosecond timestamp to datetime."""
    if ns is None:
        return None
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc)


def _ns_to_duration_ms(start_ns: int | None, end_ns: int | None) -> float | None:
    """Convert OTel nanosecond start/end to duration in milliseconds."""
    if start_ns is None or end_ns is None:
        return None
    return (end_ns - start_ns) / 1e6


class SupabaseSpanExporter(SpanExporter):
    """Exports OTel spans to Supabase agent_traces and agent_spans tables."""

    def __init__(self):
        self._supabase = None

    def _get_supabase(self):
        if self._supabase is None:
            from app.infrastructure.supabase.client import get_supabase
            self._supabase = get_supabase()
        return self._supabase

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export a batch of spans to Supabase."""
        if not spans:
            return SpanExportResult.SUCCESS

        try:
            sb = self._get_supabase()
            trace_rows = []
            span_rows = []
            # Collect aggregation data per trace
            trace_agg: dict[str, dict] = {}

            for span in spans:
                attrs = dict(span.attributes or {})
                trace_id = format(span.context.trace_id, "032x")
                span_id = format(span.context.span_id, "016x")
                parent_span_id = (
                    format(span.parent.span_id, "016x")
                    if span.parent and span.parent.span_id
                    else None
                )

                op_name = attrs.get(_OP_NAME, span.name or "unknown")
                agent_name = attrs.get(_AGENT_NAME)
                tool_name = attrs.get(_TOOL_NAME)
                model_name = attrs.get(_MODEL)
                input_tokens = attrs.get(_INPUT_TOKENS)
                output_tokens = attrs.get(_OUTPUT_TOKENS)
                finish_reasons = attrs.get(_FINISH_REASONS)
                conversation_id = attrs.get(_CONVERSATION_ID) or attrs.get(_SESSION_ID)

                started_at = _ns_to_datetime(span.start_time)
                ended_at = _ns_to_datetime(span.end_time)
                duration_ms = _ns_to_duration_ms(span.start_time, span.end_time)

                is_error = span.status and span.status.status_code == StatusCode.ERROR
                status = "error" if is_error else "ok"
                error_message = (
                    span.status.description if is_error and span.status else None
                )

                # Build span row
                span_row = {
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "operation_name": str(op_name),
                    "agent_name": str(agent_name) if agent_name else None,
                    "tool_name": str(tool_name) if tool_name else None,
                    "model_name": str(model_name) if model_name else None,
                    "started_at": started_at.isoformat() if started_at else None,
                    "ended_at": ended_at.isoformat() if ended_at else None,
                    "duration_ms": duration_ms,
                    "input_tokens": int(input_tokens) if input_tokens is not None else None,
                    "output_tokens": int(output_tokens) if output_tokens is not None else None,
                    "status": status,
                    "finish_reason": (
                        finish_reasons[0] if isinstance(finish_reasons, (list, tuple)) and finish_reasons else None
                    ),
                    "error_message": error_message,
                    "attributes": {},  # Skip large attributes to save space
                }
                span_rows.append(span_row)

                # Aggregate per trace
                if trace_id not in trace_agg:
                    trace_agg[trace_id] = {
                        "llm_calls": 0,
                        "tool_calls": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "sub_agents": set(),
                        "tools": set(),
                        "conversation_id": conversation_id,
                        "has_error": False,
                        "error_message": None,
                    }

                agg = trace_agg[trace_id]
                if conversation_id:
                    agg["conversation_id"] = conversation_id

                if op_name == "call_llm":
                    agg["llm_calls"] += 1
                    if input_tokens:
                        agg["input_tokens"] += int(input_tokens)
                    if output_tokens:
                        agg["output_tokens"] += int(output_tokens)
                elif op_name == "execute_tool" and tool_name:
                    agg["tool_calls"] += 1
                    agg["tools"].add(str(tool_name))
                elif op_name == "invoke_agent" and agent_name:
                    agg["sub_agents"].add(str(agent_name))

                if is_error:
                    agg["has_error"] = True
                    agg["error_message"] = error_message

                # Detect root invocation span → create trace row
                if span.name == "invocation" or (
                    op_name == "invoke_agent" and parent_span_id is None
                ):
                    # Extract user info from baggage-propagated attributes
                    user_email = attrs.get("user.email")
                    user_id_attr = attrs.get("user.id")

                    trace_rows.append({
                        "trace_id": trace_id,
                        "conversation_id": conversation_id,
                        "user_email": str(user_email) if user_email else None,
                        "user_id": str(user_id_attr) if user_id_attr else None,
                        "root_agent_name": str(agent_name) if agent_name else "BAndQOrchestrator",
                        "started_at": started_at.isoformat() if started_at else datetime.now(timezone.utc).isoformat(),
                        "ended_at": ended_at.isoformat() if ended_at else None,
                        "duration_ms": duration_ms,
                        "status": status,
                        "error_message": error_message,
                    })

            # Upsert trace rows first (spans have FK)
            if trace_rows:
                for row in trace_rows:
                    tid = row["trace_id"]
                    agg = trace_agg.get(tid, {})
                    row["total_llm_calls"] = agg.get("llm_calls", 0)
                    row["total_tool_calls"] = agg.get("tool_calls", 0)
                    row["total_input_tokens"] = agg.get("input_tokens", 0)
                    row["total_output_tokens"] = agg.get("output_tokens", 0)
                    row["sub_agents_used"] = sorted(agg.get("sub_agents", set()))
                    row["tools_used"] = sorted(agg.get("tools", set()))
                    if agg.get("has_error"):
                        row["status"] = "error"
                        row["error_message"] = row.get("error_message") or agg.get("error_message")
                    if agg.get("conversation_id"):
                        row["conversation_id"] = agg["conversation_id"]

                try:
                    sb.table("agent_traces").upsert(
                        trace_rows, on_conflict="trace_id"
                    ).execute()
                except Exception as e:
                    logger.warning(f"[Telemetry] Failed to upsert traces: {e}")

            # Insert spans (ignore conflicts for idempotency)
            if span_rows:
                # Only insert spans whose trace exists
                valid_trace_ids = {r["trace_id"] for r in trace_rows}
                # For spans without a trace row in this batch, create a minimal trace
                missing_traces = []
                for row in span_rows:
                    tid = row["trace_id"]
                    if tid not in valid_trace_ids:
                        valid_trace_ids.add(tid)
                        agg = trace_agg.get(tid, {})
                        missing_traces.append({
                            "trace_id": tid,
                            "conversation_id": agg.get("conversation_id"),
                            "root_agent_name": "BAndQOrchestrator",
                            "started_at": row["started_at"] or datetime.now(timezone.utc).isoformat(),
                            "status": "error" if agg.get("has_error") else "ok",
                            "total_llm_calls": agg.get("llm_calls", 0),
                            "total_tool_calls": agg.get("tool_calls", 0),
                            "total_input_tokens": agg.get("input_tokens", 0),
                            "total_output_tokens": agg.get("output_tokens", 0),
                            "sub_agents_used": sorted(agg.get("sub_agents", set())),
                            "tools_used": sorted(agg.get("tools", set())),
                        })
                if missing_traces:
                    try:
                        sb.table("agent_traces").upsert(
                            missing_traces, on_conflict="trace_id"
                        ).execute()
                    except Exception as e:
                        logger.warning(f"[Telemetry] Failed to upsert missing traces: {e}")

                try:
                    sb.table("agent_spans").upsert(
                        span_rows, on_conflict="span_id"
                    ).execute()
                except Exception as e:
                    logger.warning(f"[Telemetry] Failed to upsert spans: {e}")

            return SpanExportResult.SUCCESS

        except Exception as e:
            logger.error(f"[Telemetry] SpanExporter error: {e}", exc_info=True)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
