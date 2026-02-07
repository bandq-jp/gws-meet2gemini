"""
Plugin to optimize tool interactions for LLM token savings.

Three optimizations:
1. before_model_callback: Compress verbose tool descriptions (MCP + Zoho, ~60% input token reduction)
2. after_tool_callback: Compress GA4 report responses (~70% output token reduction)
3. Tool-level: get_module_schema picklist capping, get_record_detail null stripping (in zoho_crm_tools.py)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, TYPE_CHECKING

from google.adk.plugins.base_plugin import BasePlugin

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# Maximum rows to include in compressed output
_MAX_ROWS = 200

# ── Compressed tool descriptions ──
# Replace verbose MCP descriptions (with Hints, examples, Notes) with concise versions.
# The agent instructions already contain detailed usage guidance,
# so tool descriptions only need to explain WHAT the tool does + key parameters.
_COMPRESSED_DESCRIPTIONS: dict[str, str] = {
    # ── GA4 tools ──
    "run_report": (
        "GA4レポート実行。property_id(必須), date_ranges(必須), metrics(必須), "
        "dimensions, dimension_filter, order_bys, limit, offset, "
        "metric_filter, keep_empty_rowsを指定可能。"
        "詳細はエージェント指示文を参照。"
    ),
    "run_realtime_report": (
        "GA4リアルタイムレポート。property_id(必須), metrics(必須), "
        "dimensions, dimension_filter, limit指定可能。"
        "現在のアクティブユーザー・イベントデータを取得。"
    ),
    # ── GSC tools ──
    "get_advanced_search_analytics": (
        "GSC高度検索分析。site_url, start_date, end_date(必須), "
        "dimensions, search_type, row_limit, sort_by, "
        "filter_dimension, filter_expression, filter_operator指定可能。"
    ),
    "compare_search_periods": (
        "GSC期間比較。site_url, period1_start/end, period2_start/end(必須), "
        "dimensions, limit指定可能。2期間のパフォーマンスを比較。"
    ),
    # ── Zoho CRM tools (Tier 1) ──
    "list_crm_modules": (
        "Zoho CRM全モジュール一覧。include_record_counts=Trueで件数付き。"
    ),
    "get_module_schema": (
        "モジュールのフィールド構造取得。module_api_name(必須)。"
        "API名・型・ピックリスト値・ルックアップ先を返す。"
        "COQL WHERE句で使うフィールド名・値の確認に必須。"
    ),
    "get_module_layout": (
        "モジュールのレイアウト（セクション構造・フィールド配置）取得。module_api_name(必須)。"
    ),
    # ── Zoho CRM tools (Tier 2) ──
    "query_crm_records": (
        "任意モジュールのCOQL検索。module, fields(必須)。"
        "where, order_by, limit指定可能。LIMIT最大2000。"
    ),
    "aggregate_crm_data": (
        "任意モジュールのGROUP BY集計。module, group_by(必須)。"
        "aggregate(デフォルトCOUNT), where, limit指定可能。"
    ),
    "get_record_detail": (
        "1レコード全フィールド取得。module, record_id(必須)。"
        "null/空フィールドは除外済み。"
    ),
    "get_related_records": (
        "関連リスト・サブフォーム取得。module, record_id, related_list(必須)。"
    ),
    # ── Zoho CRM tools (Tier 3) ──
    "analyze_funnel_by_channel": (
        "jobSeekerチャネル別ファネル分析。channel(必須)。"
        "各ステージの転換率とボトルネックを自動検出。"
    ),
    "trend_analysis_by_period": (
        "期間別トレンド分析。period_type(monthly/weekly/quarterly), months_back指定可能。"
    ),
    "compare_channels": (
        "2-5チャネルの比較。channels(必須)。獲得数・入社率をランキング。"
    ),
    "get_pic_performance": (
        "担当者別パフォーマンスランキング。date_from, date_to, channel指定可能。"
    ),
    "get_conversion_metrics": (
        "全チャネル横断KPI一括取得。date_from, date_to指定可能。"
    ),
}


class MCPResponseOptimizerPlugin(BasePlugin):
    """Optimizes MCP tool definitions and responses to save LLM tokens."""

    # GA4 tools that return tabular report data
    GA4_TABULAR_TOOLS = frozenset({
        "run_report",
        "run_realtime_report",
        "run_pivot_report",
    })

    # All tools whose descriptions may need compression
    COMPRESSIBLE_TOOL_NAMES = frozenset(
        _COMPRESSED_DESCRIPTIONS.keys()
    ) | frozenset({
        # GSC tools without pre-written descriptions
        "get_search_analytics",
        "get_performance_overview",
        "get_search_by_page_query",
        "inspect_url_enhanced",
        "get_sitemaps",
    })

    def __init__(self, name: str = "mcp_response_optimizer"):
        super().__init__(name=name)

    # ── Input optimization: compress tool descriptions ──

    async def before_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> Optional[LlmResponse]:
        """Compress verbose MCP tool descriptions before sending to LLM.

        MCP tools (especially run_report) have huge descriptions with
        Hints, examples, and Notes that duplicate agent instructions.
        This strips them to essential parameter info only.

        Runs on every LLM call (overhead is negligible: ~microseconds).
        """
        try:
            compressed_count = self._compress_tool_descriptions(llm_request)
            if compressed_count > 0:
                logger.info(
                    f"[MCPOptimizer] Compressed {compressed_count} tool descriptions"
                )
        except Exception as e:
            logger.warning(f"[MCPOptimizer] Failed to compress descriptions: {e}")

        return None  # Continue to model call

    def _compress_tool_descriptions(self, llm_request: LlmRequest) -> int:
        """Modify function declarations in the LLM request to use shorter descriptions."""
        compressed = 0

        config = getattr(llm_request, "config", None)
        if config is None:
            return 0

        tools = getattr(config, "tools", None)
        if not tools:
            return 0

        for tool in tools:
            fds = getattr(tool, "function_declarations", None)
            if not fds:
                continue
            for fd in fds:
                name = getattr(fd, "name", "")
                if not name:
                    continue

                # Strategy 1: Use pre-written compressed description
                if name in _COMPRESSED_DESCRIPTIONS:
                    original_len = len(getattr(fd, "description", "") or "")
                    fd.description = _COMPRESSED_DESCRIPTIONS[name]
                    new_len = len(fd.description)
                    if original_len > new_len:
                        logger.debug(
                            f"[MCPOptimizer] {name}: {original_len} → {new_len} chars"
                        )
                        compressed += 1

                # Strategy 2: Strip verbose sections from other tools
                elif name in self.COMPRESSIBLE_TOOL_NAMES:
                    original = getattr(fd, "description", "") or ""
                    if len(original) > 200:
                        shortened = self._strip_verbose_sections(original)
                        if len(shortened) < len(original):
                            fd.description = shortened
                            compressed += 1

        return compressed

    @staticmethod
    def _strip_verbose_sections(description: str) -> str:
        """Strip Hints, Notes, and example JSON from verbose descriptions."""
        # Remove "Hints:" sections and everything after
        desc = re.sub(r'\n\s*Hints?:.*', '', description, flags=re.DOTALL)
        # Remove "Notes:" sections
        desc = re.sub(r'\n\s*Notes?:.*', '', desc, flags=re.DOTALL)
        # Remove "Example:" sections
        desc = re.sub(r'\n\s*Examples?:.*', '', desc, flags=re.DOTALL)
        # Remove JSON code blocks
        desc = re.sub(r'```json.*?```', '', desc, flags=re.DOTALL)
        # Remove excessive whitespace
        desc = re.sub(r'\n{3,}', '\n\n', desc).strip()
        return desc

    # ── Output optimization: compress GA4 report responses ──

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> Optional[dict]:
        """Intercept GA4 report responses and compress them."""
        if tool.name not in self.GA4_TABULAR_TOOLS:
            return None

        try:
            compressed = self._compress_ga4_report(result)
            if compressed is not None:
                return compressed
        except Exception as e:
            logger.warning(f"[MCPOptimizer] Failed to compress {tool.name}: {e}")

        return None  # Fall back to original result

    def _compress_ga4_report(self, result: dict) -> Optional[dict]:
        """Convert verbose GA4 report JSON to compact pipe-separated table."""
        # Extract the JSON text from MCP content
        report_data = self._extract_report_data(result)
        if report_data is None:
            return None

        dim_headers = [h.get("name", "") for h in report_data.get("dimension_headers", [])]
        met_headers = [h.get("name", "") for h in report_data.get("metric_headers", [])]
        headers = dim_headers + met_headers

        if not headers:
            return None

        rows = report_data.get("rows", [])
        row_count = report_data.get("row_count", len(rows))
        metadata = report_data.get("metadata", {})

        # Build compact table
        lines: list[str] = []

        # Header: summary line
        meta_parts = []
        if row_count:
            meta_parts.append(f"{row_count} rows")
        currency = metadata.get("currency_code", "")
        if currency:
            meta_parts.append(currency)
        tz = metadata.get("time_zone", "")
        if tz:
            meta_parts.append(tz)
        sampled = metadata.get("sampling_metadatas", [])
        if sampled:
            meta_parts.append("SAMPLED")

        lines.append(f"[GA4 Report] {' | '.join(meta_parts)}")

        # Column headers
        lines.append(" | ".join(headers))

        # Data rows (cap at _MAX_ROWS)
        truncated = len(rows) > _MAX_ROWS
        for row in rows[:_MAX_ROWS]:
            dims = [v.get("value", "") for v in row.get("dimension_values", [])]
            mets = [v.get("value", "") for v in row.get("metric_values", [])]
            lines.append(" | ".join(dims + mets))

        if truncated:
            lines.append(f"... ({row_count - _MAX_ROWS} more rows truncated)")

        # Totals if present
        totals = report_data.get("totals", [])
        if totals:
            for total_row in totals:
                mets = [v.get("value", "") for v in total_row.get("metric_values", [])]
                if any(m for m in mets):
                    lines.append(f"TOTALS: {' | '.join(mets)}")

        compressed_text = "\n".join(lines)

        # Log compression stats
        original_text = self._get_original_text(result)
        if original_text:
            original_len = len(original_text)
            compressed_len = len(compressed_text)
            ratio = (1 - compressed_len / original_len) * 100 if original_len > 0 else 0
            logger.info(
                f"[MCPOptimizer] run_report compressed: "
                f"{original_len:,} → {compressed_len:,} chars ({ratio:.0f}% reduction, "
                f"{row_count} rows)"
            )

        # Return modified result in same MCP content format
        return {
            "content": [
                {"type": "text", "text": compressed_text}
            ],
        }

    def _extract_report_data(self, result: dict) -> Optional[dict]:
        """Extract GA4 report data from MCP result dict."""
        # Case 1: MCP content format (most common)
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    if isinstance(text, str) and "dimension_headers" in text:
                        try:
                            return json.loads(text)
                        except (json.JSONDecodeError, TypeError):
                            pass

        # Case 2: Direct GA4 structure
        if "dimension_headers" in result:
            return result

        # Case 3: Nested in structuredContent
        sc = result.get("structuredContent")
        if isinstance(sc, dict):
            inner = sc.get("result", sc)
            if isinstance(inner, dict) and "dimension_headers" in inner:
                return inner

        return None

    def _get_original_text(self, result: dict) -> Optional[str]:
        """Get original text from MCP content for logging."""
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text", "")
        return None
