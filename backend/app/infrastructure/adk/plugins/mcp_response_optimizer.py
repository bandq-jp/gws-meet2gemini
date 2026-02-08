"""
Plugin to optimize tool interactions for LLM token savings.

Four optimizations:
1. before_model_callback: Compress verbose tool descriptions (MCP + Zoho + Meta, ~60% input token reduction)
2. before_model_callback: Inject pending ad image Parts into LLM context (multimodal)
3. after_tool_callback: Compress GA4/Meta Ads report responses (~70% output token reduction)
4. after_tool_callback: Intercept get_ad_image, resize to ~Full HD, convert to types.Part
"""
from __future__ import annotations

import base64
import io
import json
import logging
import re
from collections import defaultdict
from typing import Any, Optional, TYPE_CHECKING

from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# ── Image processing constants ──
# Max dimension for ad images sent to Gemini (Full HD level)
_IMAGE_MAX_DIM = 1920
# JPEG quality for resized images (85 = good quality, reasonable size)
_IMAGE_JPEG_QUALITY = 85

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
    # ── Meta Ads tools (20) ──
    "get_ad_accounts": "広告アカウント一覧取得。パラメータなし。",
    "get_account_info": "アカウント詳細。account_id(必須, act_XXX形式)。spend_cap, amount_spent, balance等。",
    "get_account_pages": "アカウント連携Facebookページ一覧。account_id(必須)。",
    "search_pages_by_name": "ページ名検索。query(必須)。",
    "get_campaigns": "キャンペーン一覧。account_id(必須), limit, status_filter指定可能。",
    "get_campaign_details": "キャンペーン詳細。campaign_id(必須)。objective, budget, status。",
    "get_adsets": "広告セット一覧。account_id(必須), campaign_id(任意フィルタ)。",
    "get_adset_details": "広告セット詳細。adset_id(必須)。targeting, optimization_goal。",
    "get_ads": "広告一覧。account_id(必須), campaign_id/adset_id(任意フィルタ)。",
    "get_ad_details": "広告詳細。ad_id(必須)。status, tracking_specs。",
    "get_ad_creatives": "クリエイティブ情報。ad_id(必須)。title, body, image, CTA。",
    "get_ad_image": "広告画像取得・可視化。ad_id(必須)。",
    "get_insights": (
        "パフォーマンス指標取得。object_id(必須: account/campaign/adset/ad ID)。"
        "time_range, date_preset, breakdown(age/gender/country/device_platform/"
        "publisher_platform/platform_position), level, action_attribution_windows指定可能。"
    ),
    "search_interests": "インタレスト検索。query(必須)。id, name, audience_size返却。",
    "get_interest_suggestions": "関連インタレスト提案。interest_list(必須)。",
    "estimate_audience_size": "オーディエンスサイズ推定。account_id, targeting(必須)。users_lower/upper_bound。",
    "validate_interests": "インタレスト有効性確認。interest_list(必須)。",
    "search_behaviors": "行動ターゲティング検索。limit指定可能。",
    "search_demographics": "デモグラ検索。demographic_class(必須: demographics/life_events/industries/income等)。",
    "search_geo_locations": "地域検索。query(必須), location_types(country/region/city/zip)。",
}


class MCPResponseOptimizerPlugin(BasePlugin):
    """Optimizes MCP tool definitions and responses to save LLM tokens."""

    # GA4 tools that return tabular report data
    GA4_TABULAR_TOOLS = frozenset({
        "run_report",
        "run_realtime_report",
        "run_pivot_report",
    })

    # Meta Ads tools that may return verbose JSON responses
    META_ADS_VERBOSE_TOOLS = frozenset({
        "get_insights",
        "get_campaigns",
        "get_adsets",
        "get_ads",
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

    # Invocation-scoped storage for image Parts waiting to be injected.
    # Key: invocation_id, Value: list of types.Part (image inline_data).
    # Populated in after_tool_callback, consumed in before_model_callback.
    _pending_images: dict[str, list] = defaultdict(list)

    def __init__(self, name: str = "mcp_response_optimizer"):
        super().__init__(name=name)

    # ── Input optimization: compress tool descriptions + inject images ──

    async def before_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> Optional[LlmResponse]:
        """Compress tool descriptions and inject pending ad image Parts.

        Two responsibilities:
        1. Replace verbose MCP tool descriptions with concise versions
        2. Inject ad creative images (from get_ad_image) directly into the
           LLM context as types.Part so Gemini can actually see them
        """
        # 1. Inject pending image Parts into LLM request
        try:
            self._inject_pending_images(callback_context, llm_request)
        except Exception as e:
            logger.warning(f"[MCPOptimizer] Failed to inject images: {e}")

        # 2. Compress tool descriptions
        try:
            compressed_count = self._compress_tool_descriptions(llm_request)
            if compressed_count > 0:
                logger.info(
                    f"[MCPOptimizer] Compressed {compressed_count} tool descriptions"
                )
        except Exception as e:
            logger.warning(f"[MCPOptimizer] Failed to compress descriptions: {e}")

        return None  # Continue to model call

    def _inject_pending_images(
        self,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> None:
        """Inject pending ad image Parts into the LLM request contents.

        When get_ad_image is called, the after_tool_callback extracts the image,
        resizes it, and stores it as a types.Part. On the next LLM call, this
        method injects those Parts into the content so Gemini can see them.
        """
        inv_id = getattr(
            getattr(callback_context, "_invocation_context", None),
            "invocation_id", None,
        )
        if not inv_id:
            return

        parts = self._pending_images.pop(inv_id, [])
        if not parts:
            return

        # Inject image Parts into the last content entry (alongside function response)
        if llm_request.contents:
            last_content = llm_request.contents[-1]
            if last_content.parts:
                last_content.parts.extend(parts)
                logger.info(
                    f"[MCPOptimizer] Injected {len(parts)} ad image(s) into LLM context"
                )
            else:
                last_content.parts = parts
        else:
            # Fallback: create new content entry
            llm_request.contents = [types.Content(role="user", parts=parts)]

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
        """Intercept GA4/Meta Ads responses and compress them.

        Also intercepts get_ad_image to extract the image, resize it,
        and store as types.Part for injection into the next LLM call.
        """
        # ── Ad image interception ──
        if tool.name == "get_ad_image":
            try:
                return self._handle_ad_image(tool_args, tool_context, result)
            except Exception as e:
                logger.warning(f"[MCPOptimizer] Failed to process ad image: {e}")
                return None

        # ── GA4 report compression ──
        if tool.name in self.GA4_TABULAR_TOOLS:
            try:
                compressed = self._compress_ga4_report(result)
                if compressed is not None:
                    return compressed
            except Exception as e:
                logger.warning(f"[MCPOptimizer] Failed to compress {tool.name}: {e}")

        # ── Meta Ads verbose response compression ──
        if tool.name in self.META_ADS_VERBOSE_TOOLS:
            try:
                compressed = self._compress_meta_ads_response(tool.name, result)
                if compressed is not None:
                    return compressed
            except Exception as e:
                logger.warning(f"[MCPOptimizer] Failed to compress Meta {tool.name}: {e}")

        return None  # Fall back to original result

    # ── Ad image processing ──

    def _handle_ad_image(
        self,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> Optional[dict]:
        """Extract ad image from MCP response, resize, store, and inject into LLM.

        Pipeline:
        1. Extract base64 from MCP Image response
        2. Resize to ~Full HD with PIL
        3. Upload to Supabase Storage → permanent public URL
        4. Create types.Part and store for before_model_callback injection
        5. Return text result with URL (agent uses it in markdown for user display)
        """
        ad_id = tool_args.get("ad_id", "unknown")

        # Extract image data from MCP content
        image_b64, mime_type = self._extract_image_from_mcp_result(result)
        if not image_b64:
            logger.info(f"[MCPOptimizer] get_ad_image(ad_id={ad_id}): no image data found")
            return None  # Let original result pass through

        # Decode base64
        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception as e:
            logger.warning(f"[MCPOptimizer] Failed to decode image base64: {e}")
            return None

        # Resize to Full HD max dimension
        resized_bytes, width, height = self._resize_ad_image(image_bytes)

        # Create types.Part for Gemini multimodal
        image_part = types.Part.from_bytes(
            data=resized_bytes,
            mime_type=mime_type or "image/jpeg",
        )

        # Store in pending images, keyed by invocation_id
        inv_id = getattr(
            getattr(tool_context, "_invocation_context", None),
            "invocation_id", None,
        )
        if inv_id:
            self._pending_images[inv_id].append(image_part)
            logger.info(
                f"[MCPOptimizer] Ad image stored for injection: "
                f"ad_id={ad_id}, {width}x{height}, "
                f"{len(resized_bytes):,} bytes, inv={inv_id[:8]}..."
            )
        else:
            logger.warning("[MCPOptimizer] No invocation_id — image cannot be injected")

        # Upload to Supabase Storage for permanent URL
        image_url = self._upload_ad_image_to_storage(ad_id, resized_bytes)

        # Build result text
        if image_url:
            result_text = (
                f"[Ad image: ad_id={ad_id}, {width}x{height}px, "
                f"{len(resized_bytes) // 1024}KB]\n"
                f"Image URL: {image_url}\n"
                f"この画像はあなたのコンテキストに読み込み済みです（視覚分析可能）。\n"
                f"ユーザーに画像を見せるには ![広告画像](Image URL) を回答に含めてください。"
            )
        else:
            result_text = (
                f"[Ad image: ad_id={ad_id}, {width}x{height}px, "
                f"{len(resized_bytes) // 1024}KB]\n"
                f"この画像はあなたのコンテキストに読み込み済みです（視覚分析可能）。\n"
                f"（Storage URLは取得できませんでした。画像分析は可能です。）"
            )

        return {"content": [{"type": "text", "text": result_text}]}

    @staticmethod
    def _upload_ad_image_to_storage(ad_id: str, image_bytes: bytes) -> Optional[str]:
        """Upload ad image to Supabase Storage and return signed URL.

        Saves to: marketing-attachments/ad-images/ad_{ad_id}_{timestamp}.jpg
        Returns signed URL (7-day expiry) or None on failure.
        """
        import time

        try:
            from app.infrastructure.supabase.client import get_supabase
            sb = get_supabase()
            timestamp = int(time.time())
            storage_path = f"ad-images/ad_{ad_id}_{timestamp}.jpg"

            sb.storage.from_("marketing-attachments").upload(
                storage_path,
                image_bytes,
                file_options={"content-type": "image/jpeg"},
            )

            # Use signed URL (7 days) since bucket is private
            res = sb.storage.from_("marketing-attachments").create_signed_url(
                storage_path, expires_in=604800  # 7 days
            )
            url = res.get("signedURL", "") if isinstance(res, dict) else ""
            if url:
                logger.info(f"[MCPOptimizer] Ad image uploaded: {storage_path}")
                return url

            logger.warning("[MCPOptimizer] Signed URL creation returned empty")
            return None
        except Exception as e:
            logger.warning(f"[MCPOptimizer] Failed to upload ad image to storage: {e}")
            return None

    @staticmethod
    def _extract_image_from_mcp_result(
        result: dict,
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract base64 image data and MIME type from MCP result.

        MCP Image responses are serialized by ADK as:
        {"content": [{"type": "image", "data": "<base64>", "mimeType": "image/jpeg"}]}

        Returns (base64_data, mime_type) or (None, None).
        """
        content = result.get("content")
        if not isinstance(content, list):
            return None, None

        for item in content:
            if not isinstance(item, dict):
                continue
            # MCP Image type
            if item.get("type") == "image":
                data = item.get("data", "")
                mime = item.get("mimeType") or item.get("mime_type") or "image/jpeg"
                if data:
                    return data, mime

        return None, None

    @staticmethod
    def _resize_ad_image(image_bytes: bytes) -> tuple[bytes, int, int]:
        """Resize ad image to max Full HD dimension, return (jpeg_bytes, width, height).

        Uses PIL/Pillow for high-quality Lanczos resampling.
        If the image is already smaller than _IMAGE_MAX_DIM, it is returned as-is
        (re-encoded as JPEG for consistent format).
        """
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary (handles RGBA, palette, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        width, height = img.size

        # Resize if either dimension exceeds max
        if max(width, height) > _IMAGE_MAX_DIM:
            scale = _IMAGE_MAX_DIM / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), PILImage.LANCZOS)
            width, height = new_width, new_height
            logger.info(
                f"[MCPOptimizer] Ad image resized: {img.size[0]}x{img.size[1]} → {width}x{height}"
            )

        # Encode as JPEG
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_IMAGE_JPEG_QUALITY, optimize=True)
        return buf.getvalue(), width, height

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

    # ── Meta Ads response optimization ──

    def _compress_meta_ads_response(
        self, tool_name: str, result: dict
    ) -> Optional[dict]:
        """Compress verbose Meta Ads MCP responses to compact format.

        Meta Ads responses often contain deeply nested JSON with redundant
        fields (targeting specs, empty arrays, null values, pagination metadata).
        This strips them to essential data only.
        """
        original_text = self._get_original_text(result)
        if not original_text:
            return None

        # Only compress if response is large enough to benefit
        if len(original_text) < 500:
            return None

        try:
            data = json.loads(original_text)
        except (json.JSONDecodeError, TypeError):
            return None

        if tool_name == "get_insights":
            compressed = self._compress_insights_data(data)
        elif tool_name in ("get_campaigns", "get_adsets", "get_ads"):
            compressed = self._compress_list_data(tool_name, data)
        else:
            return None

        if compressed is None:
            return None

        compressed_text = compressed if isinstance(compressed, str) else json.dumps(compressed, ensure_ascii=False)

        original_len = len(original_text)
        compressed_len = len(compressed_text)
        ratio = (1 - compressed_len / original_len) * 100 if original_len > 0 else 0
        logger.info(
            f"[MCPOptimizer] Meta {tool_name} compressed: "
            f"{original_len:,} → {compressed_len:,} chars ({ratio:.0f}% reduction)"
        )

        return {"content": [{"type": "text", "text": compressed_text}]}

    def _compress_insights_data(self, data: Any) -> Optional[str]:
        """Convert Meta Ads insights to compact pipe-separated table."""
        # Handle various response structures
        insights = None
        if isinstance(data, dict):
            insights = data.get("data") or data.get("insights", {}).get("data")
            if not insights and "impressions" in data:
                # Single row directly
                insights = [data]
        elif isinstance(data, list):
            insights = data

        if not insights or not isinstance(insights, list):
            return None

        # Collect all unique keys across all insight rows
        all_keys: list[str] = []
        seen_keys: set[str] = set()

        # Priority keys to show first
        priority_keys = [
            "campaign_name", "adset_name", "ad_name",
            "date_start", "date_stop",
            "impressions", "reach", "frequency",
            "clicks", "ctr", "cpc", "cpm",
            "spend", "conversions", "cost_per_conversion",
            "purchase_roas",
            "quality_ranking", "engagement_rate_ranking", "conversion_rate_ranking",
        ]

        for key in priority_keys:
            for row in insights:
                if isinstance(row, dict) and key in row:
                    if key not in seen_keys:
                        all_keys.append(key)
                        seen_keys.add(key)
                    break

        # Add remaining keys (skip verbose/nested ones)
        _skip_keys = {
            "account_id", "account_name", "account_currency",
            "canvas_avg_view_percent", "canvas_avg_view_time",
            "date_start", "date_stop",  # Already added if present
        }
        for row in insights[:1]:
            if isinstance(row, dict):
                for key in row:
                    if key not in seen_keys and key not in _skip_keys:
                        val = row[key]
                        # Skip complex nested structures (actions, action_values, etc.)
                        if isinstance(val, (list, dict)):
                            continue
                        all_keys.append(key)
                        seen_keys.add(key)

        if not all_keys:
            return None

        # Build compact table
        lines: list[str] = []
        lines.append(f"[Meta Insights] {len(insights)} rows")
        lines.append(" | ".join(all_keys))

        for row in insights[:_MAX_ROWS]:
            if not isinstance(row, dict):
                continue
            values = []
            for key in all_keys:
                val = row.get(key, "")
                if val is None:
                    val = ""
                values.append(str(val))
            lines.append(" | ".join(values))

        if len(insights) > _MAX_ROWS:
            lines.append(f"... ({len(insights) - _MAX_ROWS} more rows truncated)")

        # Append actions summary if present (flattened)
        for row in insights[:3]:
            if isinstance(row, dict):
                actions = row.get("actions")
                if isinstance(actions, list) and actions:
                    action_summary = []
                    for a in actions[:10]:
                        if isinstance(a, dict):
                            atype = a.get("action_type", "?")
                            aval = a.get("value", "?")
                            action_summary.append(f"{atype}={aval}")
                    if action_summary:
                        row_label = row.get("campaign_name") or row.get("adset_name") or row.get("date_start", "")
                        lines.append(f"Actions({row_label}): {', '.join(action_summary)}")

                cost_actions = row.get("cost_per_action_type")
                if isinstance(cost_actions, list) and cost_actions:
                    cpa_summary = []
                    for a in cost_actions[:10]:
                        if isinstance(a, dict):
                            atype = a.get("action_type", "?")
                            aval = a.get("value", "?")
                            cpa_summary.append(f"{atype}=${aval}")
                    if cpa_summary:
                        row_label = row.get("campaign_name") or row.get("adset_name") or row.get("date_start", "")
                        lines.append(f"CostPerAction({row_label}): {', '.join(cpa_summary)}")

        return "\n".join(lines)

    def _compress_list_data(self, tool_name: str, data: Any) -> Optional[str]:
        """Compress campaign/adset/ad list responses by stripping verbose fields."""
        items = None
        if isinstance(data, dict):
            items = data.get("data")
        elif isinstance(data, list):
            items = data

        if not items or not isinstance(items, list):
            return None

        # Only compress if sufficiently large
        if len(items) < 3:
            return None

        # Strip verbose nested fields, keep essential ones
        _essential_fields = {
            "get_campaigns": {"id", "name", "status", "objective", "daily_budget", "lifetime_budget", "effective_status", "created_time", "updated_time", "buying_type", "bid_strategy"},
            "get_adsets": {"id", "name", "status", "campaign_id", "daily_budget", "lifetime_budget", "optimization_goal", "billing_event", "bid_amount", "bid_strategy", "effective_status", "start_time", "end_time"},
            "get_ads": {"id", "name", "status", "adset_id", "campaign_id", "effective_status", "created_time"},
        }

        keep_fields = _essential_fields.get(tool_name, set())
        if not keep_fields:
            return None

        cleaned = []
        for item in items:
            if isinstance(item, dict):
                clean_item = {k: v for k, v in item.items() if k in keep_fields and v is not None}
                cleaned.append(clean_item)

        return json.dumps(cleaned, ensure_ascii=False)
