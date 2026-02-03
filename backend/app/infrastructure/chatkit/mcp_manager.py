"""
MCP Server Manager for Local STDIO-based MCP servers.

This module manages the lifecycle of local MCP servers (GA4, GSC) that run as
subprocesses, providing significantly faster initialization compared to remote
Cloud Run-hosted MCP servers.

Usage:
    manager = MCPSessionManager(settings)
    pair = manager.create_server_pair()

    async with AsyncExitStack() as stack:
        if pair.ga4_server:
            await stack.enter_async_context(pair.ga4_server)
        if pair.gsc_server:
            await stack.enter_async_context(pair.gsc_server)

        # Use servers...
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from agents.mcp import MCPServerStdio
from agents.mcp.server import MCPServerStdioParams

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class MCPServerPair:
    """Container for local MCP server instances."""
    ga4_server: MCPServerStdio | None = None
    gsc_server: MCPServerStdio | None = None
    meta_ads_server: MCPServerStdio | None = None


class MCPSessionManager:
    """
    Manages local MCP server lifecycle using STDIO transport.

    Local MCP servers provide ~50x faster initialization compared to
    Cloud Run-hosted servers (1-2s vs 15-30s).
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._gsc_script_path = self._resolve_gsc_script_path()

    def _resolve_gsc_script_path(self) -> str:
        """Resolve the path to the GSC MCP server script."""
        # Relative to this file: ../../../scripts/gsc_server.py
        current_dir = Path(__file__).parent
        script_path = current_dir / ".." / ".." / ".." / "scripts" / "gsc_server.py"
        resolved = script_path.resolve()
        if not resolved.exists():
            logger.warning(f"GSC MCP server script not found at: {resolved}")
        return str(resolved)

    def _get_service_account_path(self) -> str:
        """
        Get the service account JSON file path.

        Supports both file path and inline JSON string formats.
        For inline JSON, the path itself is returned (analytics-mcp handles both).
        """
        sa_json = self._settings.service_account_json
        if not sa_json:
            raise ValueError("SERVICE_ACCOUNT_JSON is not configured")

        # If it's a file path and exists, return it
        if os.path.exists(sa_json):
            return os.path.abspath(sa_json)

        # If it looks like JSON (starts with '{'), it's inline JSON
        # analytics-mcp expects a file path, so we need to write it to a temp file
        if sa_json.strip().startswith("{"):
            import tempfile
            import json

            # Validate it's valid JSON
            try:
                json.loads(sa_json)
            except json.JSONDecodeError as e:
                raise ValueError(f"SERVICE_ACCOUNT_JSON is neither a valid file path nor valid JSON: {e}")

            # Write to temp file
            fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="sa_")
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(sa_json)
                logger.info(f"Created temporary service account file: {temp_path}")
                return temp_path
            except Exception:
                os.close(fd)
                raise

        # Assume it's a path that might be created later
        return sa_json

    def create_ga4_server(self) -> MCPServerStdio:
        """
        Create a GA4 MCP server instance using analytics-mcp package.

        The server runs as a subprocess and uses GOOGLE_APPLICATION_CREDENTIALS
        for authentication via the existing service account.
        """
        sa_path = self._get_service_account_path()
        gcp_project = self._settings.gcp_project

        if not gcp_project:
            logger.warning("GCP_PROJECT is not set, GA4 MCP may not work correctly")

        return MCPServerStdio(
            params=MCPServerStdioParams(
                command="analytics-mcp",
                args=[],
                env={
                    "GOOGLE_APPLICATION_CREDENTIALS": sa_path,
                    "GOOGLE_CLOUD_PROJECT": gcp_project,
                    "GCLOUD_PROJECT": gcp_project,
                },
            ),
            cache_tools_list=True,
            client_session_timeout_seconds=float(self._settings.mcp_client_timeout_seconds),
        )

    def create_gsc_server(self) -> MCPServerStdio:
        """
        Create a GSC MCP server instance using custom FastMCP server.

        The server runs as a subprocess and uses GOOGLE_APPLICATION_CREDENTIALS
        for authentication via the existing service account.
        """
        sa_path = self._get_service_account_path()

        if not os.path.exists(self._gsc_script_path):
            raise FileNotFoundError(
                f"GSC MCP server script not found: {self._gsc_script_path}. "
                "Please ensure backend/scripts/gsc_server.py exists."
            )

        return MCPServerStdio(
            params=MCPServerStdioParams(
                command=sys.executable,
                args=[self._gsc_script_path],
                env={
                    "GOOGLE_APPLICATION_CREDENTIALS": sa_path,
                },
            ),
            cache_tools_list=True,
            client_session_timeout_seconds=float(self._settings.mcp_client_timeout_seconds),
        )

    def create_meta_ads_server(self) -> MCPServerStdio | None:
        """
        Create a Meta Ads MCP server instance using meta-ads-mcp package.

        The server runs as a subprocess and uses META_ACCESS_TOKEN for authentication.
        Returns None if META_ACCESS_TOKEN is not configured.
        """
        meta_access_token = self._settings.meta_access_token
        if not meta_access_token:
            return None

        return MCPServerStdio(
            params=MCPServerStdioParams(
                command="meta-ads-mcp",
                args=[],
                env={
                    "META_ACCESS_TOKEN": meta_access_token,
                    "META_ADS_DISABLE_CALLBACK_SERVER": "1",
                },
            ),
            cache_tools_list=True,
            client_session_timeout_seconds=float(self._settings.mcp_client_timeout_seconds),
        )

    def create_server_pair(self) -> MCPServerPair:
        """
        Create MCP servers based on settings.

        Returns:
            MCPServerPair with GA4, GSC, and/or Meta Ads servers based on configuration.
        """
        ga4_server = None
        gsc_server = None
        meta_ads_server = None

        # GA4 MCP
        if self._settings.local_mcp_ga4_enabled:
            try:
                ga4_server = self.create_ga4_server()
                logger.info("[Local MCP] GA4: ready (analytics-mcp)")
            except Exception as e:
                logger.error(f"[Local MCP] GA4: FAILED - {e}")

        # GSC MCP
        if self._settings.local_mcp_gsc_enabled:
            try:
                gsc_server = self.create_gsc_server()
                logger.info("[Local MCP] GSC: ready (gsc_server.py)")
            except Exception as e:
                logger.error(f"[Local MCP] GSC: FAILED - {e}")

        # Meta Ads MCP
        if self._settings.local_mcp_meta_ads_enabled:
            try:
                meta_ads_server = self.create_meta_ads_server()
                if meta_ads_server:
                    logger.info("[Local MCP] Meta Ads: ready (meta-ads-mcp)")
                else:
                    logger.info("[Local MCP] Meta Ads: skipped (no META_ACCESS_TOKEN, will use hosted if configured)")
            except Exception as e:
                logger.error(f"[Local MCP] Meta Ads: FAILED - {e}")

        # Summary
        enabled_count = sum(1 for s in [ga4_server, gsc_server, meta_ads_server] if s is not None)
        logger.info(f"[Local MCP] Total: {enabled_count}/3 servers ready")

        return MCPServerPair(
            ga4_server=ga4_server,
            gsc_server=gsc_server,
            meta_ads_server=meta_ads_server,
        )
