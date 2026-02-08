"""
MCP Manager for Google ADK.

Manages MCP toolset creation and lifecycle for ADK agents.
Uses McpToolset with STDIO or SSE connections.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional

from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams, StdioServerParameters

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

# ── Tool filters to reduce input tokens ──
# Only expose essential tools to the LLM (excludes rarely-used admin/utility tools)

# GA4 (analytics-mcp): 6→2 tools
# Keep: run_report (primary), run_realtime_report
# Drop: get_account_summaries, list_google_ads_links, get_property_details,
#        get_custom_dimensions_and_metrics
GA4_TOOL_FILTER = ["run_report", "run_realtime_report"]

# GSC (gsc_server.py): 9→6 tools
# Keep: search analytics, overview, advanced, compare, page query, url inspect
# Drop: list_properties (hardcoded in agent), get_site_details, batch_url_inspection
GSC_TOOL_FILTER = [
    "get_search_analytics",
    "get_performance_overview",
    "get_advanced_search_analytics",
    "compare_search_periods",
    "get_search_by_page_query",
    "inspect_url_enhanced",
    "get_sitemaps",
]


@dataclass
class ADKMCPToolsets:
    """Container for ADK MCP toolsets."""
    ga4: Optional[McpToolset] = None
    gsc: Optional[McpToolset] = None
    meta_ads: Optional[McpToolset] = None
    ahrefs: Optional[McpToolset] = None
    wordpress_hitocareer: Optional[McpToolset] = None
    wordpress_achievehr: Optional[McpToolset] = None

    def all(self) -> List[McpToolset]:
        """Return all available toolsets."""
        return [t for t in [
            self.ga4, self.gsc, self.meta_ads, self.ahrefs,
            self.wordpress_hitocareer, self.wordpress_achievehr
        ] if t is not None]


class ADKMCPManager:
    """
    Manager for ADK MCP toolsets.

    Creates and manages MCP toolsets for various services:
    - GA4 (Google Analytics 4) - STDIO
    - GSC (Google Search Console) - STDIO
    - Meta Ads - STDIO
    - Ahrefs - SSE (future)
    - WordPress - SSE (future)
    """

    def __init__(self, settings: "Settings"):
        self._settings = settings

    def _resolve_service_account_path(self) -> Optional[str]:
        """Resolve Google service account path or inline JSON."""
        sa_config = self._settings.service_account_json
        if not sa_config:
            return None

        # Check if it's a file path
        if os.path.isfile(sa_config):
            return sa_config

        # Check if it's inline JSON - write to temp file
        if sa_config.strip().startswith("{"):
            import tempfile
            import json
            try:
                # Validate JSON
                json.loads(sa_config)
                # Write to temp file
                fd, path = tempfile.mkstemp(suffix=".json", prefix="sa_")
                with os.fdopen(fd, "w") as f:
                    f.write(sa_config)
                return path
            except json.JSONDecodeError:
                logger.warning("[ADK MCP] Invalid inline JSON for service account")
                return None

        return None

    async def create_ga4_toolset(self) -> Optional[McpToolset]:
        """Create GA4 MCP toolset using STDIO transport."""
        if not self._settings.use_local_mcp or not self._settings.local_mcp_ga4_enabled:
            logger.info("[ADK MCP] GA4: skipped (disabled)")
            return None

        sa_path = self._resolve_service_account_path()
        if not sa_path:
            logger.warning("[ADK MCP] GA4: skipped (no service account)")
            return None

        try:
            # Use configurable timeout (default 120s) instead of ADK's default 5s
            timeout = float(self._settings.mcp_client_timeout_seconds)
            toolset = McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="analytics-mcp",
                        args=[],
                        env={"GOOGLE_APPLICATION_CREDENTIALS": sa_path},
                    ),
                    timeout=timeout,  # Override default 5s timeout
                ),
                # Filter to essential tools only (6→2) to reduce input tokens
                # Excluded: get_account_summaries, list_google_ads_links,
                #           get_property_details, get_custom_dimensions_and_metrics
                tool_filter=GA4_TOOL_FILTER,
            )
            logger.info("[ADK MCP] GA4: ready (analytics-mcp, timeout=%ds, tools=%s)", int(timeout), GA4_TOOL_FILTER)
            return toolset
        except Exception as e:
            logger.warning(f"[ADK MCP] GA4: failed to create toolset: {e}")
            return None

    async def create_gsc_toolset(self) -> Optional[McpToolset]:
        """Create GSC MCP toolset using STDIO transport."""
        if not self._settings.use_local_mcp or not self._settings.local_mcp_gsc_enabled:
            logger.info("[ADK MCP] GSC: skipped (disabled)")
            return None

        sa_path = self._resolve_service_account_path()
        if not sa_path:
            logger.warning("[ADK MCP] GSC: skipped (no service account)")
            return None

        # Find gsc_server.py path
        import sys
        scripts_dir = os.path.join(os.path.dirname(sys.modules["app"].__file__), "..", "scripts")
        gsc_server_path = os.path.join(scripts_dir, "gsc_server.py")

        if not os.path.exists(gsc_server_path):
            # Try alternative path
            gsc_server_path = os.path.join(os.getcwd(), "scripts", "gsc_server.py")

        if not os.path.exists(gsc_server_path):
            logger.warning(f"[ADK MCP] GSC: skipped (gsc_server.py not found)")
            return None

        try:
            timeout = float(self._settings.mcp_client_timeout_seconds)
            toolset = McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="python",
                        args=[gsc_server_path],
                        env={"GOOGLE_APPLICATION_CREDENTIALS": sa_path},
                    ),
                    timeout=timeout,  # Override default 5s timeout
                ),
                # Filter to essential tools only (9→6) to reduce input tokens
                # Excluded: list_properties, get_site_details, batch_url_inspection
                tool_filter=GSC_TOOL_FILTER,
            )
            logger.info("[ADK MCP] GSC: ready (gsc_server.py, timeout=%ds, tools=%s)", int(timeout), GSC_TOOL_FILTER)
            return toolset
        except Exception as e:
            logger.warning(f"[ADK MCP] GSC: failed to create toolset: {e}")
            return None

    async def create_meta_ads_toolset(self) -> Optional[McpToolset]:
        """Create Meta Ads MCP toolset using STDIO transport."""
        if not self._settings.use_local_mcp or not self._settings.local_mcp_meta_ads_enabled:
            logger.info("[ADK MCP] Meta Ads: skipped (disabled)")
            return None

        if not self._settings.meta_access_token:
            logger.info("[ADK MCP] Meta Ads: skipped (no META_ACCESS_TOKEN)")
            return None

        try:
            timeout = float(self._settings.mcp_client_timeout_seconds)
            toolset = McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="meta-ads-mcp",
                        args=[],
                        env={"META_ACCESS_TOKEN": self._settings.meta_access_token},
                    ),
                    timeout=timeout,  # Override default 5s timeout
                ),
            )
            logger.info("[ADK MCP] Meta Ads: ready (meta-ads-mcp, timeout=%ds)", int(timeout))
            return toolset
        except Exception as e:
            logger.warning(f"[ADK MCP] Meta Ads: failed to create toolset: {e}")
            return None

    async def create_toolsets(self) -> ADKMCPToolsets:
        """Create all available MCP toolsets."""
        toolsets = ADKMCPToolsets()

        if self._settings.use_local_mcp:
            toolsets.ga4 = await self.create_ga4_toolset()
            toolsets.gsc = await self.create_gsc_toolset()
            toolsets.meta_ads = await self.create_meta_ads_toolset()

        available = len([t for t in [toolsets.ga4, toolsets.gsc, toolsets.meta_ads] if t])
        logger.info(f"[ADK MCP] Total: {available}/3 toolsets ready")

        return toolsets
