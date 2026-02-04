"""
Compact MCP Server Wrapper
===========================
MCPServerStdio をラップし、GA4 の verbose な proto_to_dict JSON 出力を
compact TSV 形式に変換してトークン消費を ~76% 削減する。

Ported from: /home/als0028/study/shintairiku/ga4-oauth-aiagent/backend/app/services/compact_mcp.py
"""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

from mcp import Tool as MCPTool
from mcp.types import (
    CallToolResult,
    GetPromptResult,
    ListPromptsResult,
    TextContent,
)

if TYPE_CHECKING:
    from agents.mcp.server import MCPServer
    from agents.run_context import RunContextWrapper
    from agents.agent import AgentBase

logger = logging.getLogger(__name__)

# Tools whose output should be compacted (GA4 report tools)
_COMPACT_TOOLS = frozenset({"run_report", "run_realtime_report"})


def _compact_ga4_report(raw_json: str) -> str:
    """Convert verbose GA4 proto_to_dict JSON into compact TSV.

    Input format (proto_to_dict):
        {
          "dimension_headers": [{"name": "date"}, ...],
          "metric_headers": [{"name": "sessions", "type_": "TYPE_INTEGER"}, ...],
          "rows": [
            {
              "dimension_values": [{"value": "20260127"}, ...],
              "metric_values": [{"value": "153"}, ...]
            }, ...
          ],
          "row_count": 140,
          "totals": [], "maximums": [], "minimums": [], "kind": ""
        }

    Output format (compact TSV):
        date\tchannel\tsessions\tactiveUsers
        20260127\tOrganic Search\t153\t130
        ...
        ---
        rows: 140
    """
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return raw_json  # Not JSON, return as-is

    if not isinstance(data, dict):
        return raw_json

    dim_headers = data.get("dimension_headers") or data.get("dimensionHeaders")
    metric_headers = data.get("metric_headers") or data.get("metricHeaders")
    rows = data.get("rows")

    if not dim_headers or not metric_headers or not rows:
        return raw_json  # Not a report response, return as-is

    # Build header row
    dim_names = [h.get("name", "") for h in dim_headers]
    metric_names = [h.get("name", "") for h in metric_headers]
    header = "\t".join(dim_names + metric_names)

    # Build data rows
    lines = [header]
    for row in rows:
        dim_vals = row.get("dimension_values") or row.get("dimensionValues") or []
        met_vals = row.get("metric_values") or row.get("metricValues") or []

        dim_strs = [v.get("value", "") for v in dim_vals]
        met_strs = [v.get("value", "") for v in met_vals]
        lines.append("\t".join(dim_strs + met_strs))

    # Add metadata footer
    row_count = data.get("row_count") or data.get("rowCount") or len(rows)
    lines.append("---")
    lines.append(f"rows: {row_count}")

    result = "\n".join(lines)
    original_len = len(raw_json)
    result_len = len(result)
    reduction = 100 - (result_len * 100 // max(original_len, 1))
    logger.info(f"[CompactMCP] GA4 report: {original_len} → {result_len} chars ({reduction}% reduction)")
    return result


class CompactMCPServer:
    """Proxy that wraps an MCPServer and compresses verbose tool outputs.

    Implements the same interface as MCPServer so the Agents SDK treats it
    as a regular MCP server. Delegates all calls to the inner server,
    but transforms call_tool outputs for specific tools.

    Also enforces a max character limit on ALL tool outputs to prevent
    context window overflow.
    """

    def __init__(self, inner: Any, max_output_chars: int = 16000):
        self._inner = inner
        self._max_output_chars = max_output_chars

    # --- Proxied properties ---

    @property
    def name(self) -> str:
        return self._inner.name

    # Forward any attribute access to inner server (cache_tools_list, etc.)
    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    # --- Context manager ---

    async def __aenter__(self):
        await self._inner.__aenter__()
        return self

    async def __aexit__(self, *args):
        return await self._inner.__aexit__(*args)

    # --- MCPServer interface ---

    async def connect(self):
        return await self._inner.connect()

    async def cleanup(self):
        return await self._inner.cleanup()

    async def list_tools(
        self,
        run_context: Any = None,
        agent: Any = None,
    ) -> list[MCPTool]:
        return await self._inner.list_tools(run_context, agent)

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None
    ) -> CallToolResult:
        result = await self._inner.call_tool(tool_name, arguments)

        if not result or not hasattr(result, "content") or not result.content:
            return result

        new_content = []
        for item in result.content:
            if not hasattr(item, "text") or not item.text:
                new_content.append(item)
                continue

            text = item.text

            # Apply GA4 report compaction for specific tools
            if tool_name in _COMPACT_TOOLS:
                text = _compact_ga4_report(text)

            # Enforce max output character limit
            if len(text) > self._max_output_chars:
                # For TSV: truncate by lines to keep data coherent
                lines = text.split("\n")
                truncated_lines = []
                char_count = 0
                for line in lines:
                    if char_count + len(line) + 1 > self._max_output_chars - 80:
                        break
                    truncated_lines.append(line)
                    char_count += len(line) + 1
                total_lines = len(lines)
                kept_lines = len(truncated_lines)
                truncated_lines.append("---")
                truncated_lines.append(
                    f"[truncated: showing {kept_lines}/{total_lines} lines, "
                    f"{self._max_output_chars} char limit]"
                )
                text = "\n".join(truncated_lines)
                logger.info(
                    f"[CompactMCP] Truncated {tool_name}: {kept_lines}/{total_lines} lines"
                )

            new_content.append(TextContent(type="text", text=text))

        return CallToolResult(content=new_content, isError=result.isError)

    async def list_prompts(self) -> ListPromptsResult:
        return await self._inner.list_prompts()

    async def get_prompt(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> GetPromptResult:
        return await self._inner.get_prompt(name, arguments)
