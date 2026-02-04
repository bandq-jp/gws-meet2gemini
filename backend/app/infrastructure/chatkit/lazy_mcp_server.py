"""
Lazy MCP Server Wrapper - Defers connection until first tool access.

This wrapper dramatically improves response time for queries that don't
require MCP tools (e.g., simple greetings, general knowledge questions).

Architecture:
- MCP servers are ONLY used by sub-agents
- Sub-agents are ONLY called when orchestrator decides to delegate
- Simple queries don't call sub-agents → MCP initialization is wasted

With LazyMCPServer:
- No connection at initialization
- Connection happens on first list_tools() or call_tool()
- Saves 2-3 seconds per MCP server for non-tool queries

With CompactMCPServer integration:
- GA4 report outputs are compressed from JSON to TSV (~76% reduction)
- Prevents context window overflow
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, Awaitable

from .compact_mcp import CompactMCPServer

if TYPE_CHECKING:
    from agents.mcp import MCPServer

logger = logging.getLogger(__name__)


class LazyMCPServer:
    """
    Proxy wrapper that defers MCP server connection until first use.

    This wrapper is transparent to the Agent SDK - it implements the same
    interface as MCPServer and can be used anywhere MCPServer is expected.

    Example:
        # Instead of connecting eagerly:
        server = MCPServerStdio(...)
        await server.connect()  # Blocks for ~1 second

        # Use lazy wrapper:
        lazy_server = LazyMCPServer(
            server_factory=lambda: MCPServerStdio(...),
            name="ga4"
        )
        # No connection yet - instant return

        # Connection happens on first tool access:
        tools = await lazy_server.list_tools()  # Connects here
    """

    def __init__(
        self,
        server_factory: Callable[[], "MCPServer"],
        name: str = "lazy-mcp",
        cache_tools_list: bool = True,
        use_compact_wrapper: bool = False,
        max_output_chars: int = 16000,
    ):
        """
        Initialize lazy MCP server wrapper.

        Args:
            server_factory: Callable that creates the underlying MCPServer.
                           Called lazily on first use.
            name: Server name (for logging).
            cache_tools_list: Whether to cache tool list after first fetch.
            use_compact_wrapper: Whether to wrap with CompactMCPServer (for GA4).
            max_output_chars: Max chars for tool output (CompactMCPServer).
        """
        self._server_factory = server_factory
        self._name = name
        self._cache_tools_list = cache_tools_list
        self._use_compact_wrapper = use_compact_wrapper
        self._max_output_chars = max_output_chars
        self._server: "MCPServer" | None = None
        self._connected = False
        self._connecting = False
        self._connect_lock = asyncio.Lock()
        self._cached_tools: list | None = None

    @property
    def name(self) -> str:
        """Return server name."""
        return self._name

    async def _ensure_connected(self) -> "MCPServer":
        """
        Ensure the underlying server is created and connected.

        Thread-safe via asyncio.Lock to prevent multiple connections.
        """
        if self._connected and self._server:
            return self._server

        async with self._connect_lock:
            # Double-check after acquiring lock
            if self._connected and self._server:
                return self._server

            if self._connecting:
                # Wait for other task to complete connection
                while self._connecting:
                    await asyncio.sleep(0.01)
                if self._connected and self._server:
                    return self._server

            self._connecting = True
            try:
                logger.info(f"[LazyMCP] Connecting {self._name}...")

                # Create server instance
                inner_server = self._server_factory()

                # Wrap with CompactMCPServer if enabled (for GA4)
                if self._use_compact_wrapper:
                    self._server = CompactMCPServer(inner_server, self._max_output_chars)
                    logger.info(f"[LazyMCP] {self._name} wrapped with CompactMCPServer")
                else:
                    self._server = inner_server

                # Connect (this is the expensive operation)
                await self._server.__aenter__()

                self._connected = True
                logger.info(f"[LazyMCP] {self._name} connected")

                return self._server
            except Exception as e:
                logger.error(f"[LazyMCP] {self._name} connection failed: {e}")
                self._server = None
                raise
            finally:
                self._connecting = False

    async def list_tools(self, run_context=None, agent=None) -> list:
        """
        List available tools from the MCP server.

        Connection is established on first call.
        Results are cached if cache_tools_list=True.
        """
        # Return cached if available
        if self._cache_tools_list and self._cached_tools is not None:
            return self._cached_tools

        server = await self._ensure_connected()
        tools = await server.list_tools(run_context, agent)

        if self._cache_tools_list:
            self._cached_tools = tools

        return tools

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        Call a tool on the MCP server.

        Connection is established on first call.
        """
        server = await self._ensure_connected()
        return await server.call_tool(tool_name, arguments)

    async def cleanup(self) -> None:
        """
        Clean up the underlying server if connected.
        """
        if self._server and self._connected:
            try:
                await self._server.__aexit__(None, None, None)
                logger.info(f"[LazyMCP] {self._name} cleaned up")
            except Exception as e:
                logger.warning(f"[LazyMCP] {self._name} cleanup error: {e}")
            finally:
                self._server = None
                self._connected = False
                self._cached_tools = None

    async def __aenter__(self) -> "LazyMCPServer":
        """
        Async context manager entry - does NOT connect yet.

        This is key to lazy behavior: entering the context manager
        does not establish the connection. Connection is deferred
        until first tool access.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Async context manager exit - cleans up if connected.
        """
        await self.cleanup()

    @property
    def is_connected(self) -> bool:
        """Check if the underlying server is connected."""
        return self._connected

    def invalidate_tools_cache(self) -> None:
        """Invalidate the cached tools list."""
        self._cached_tools = None


class LazyMCPServerPair:
    """
    Container for lazy MCP servers.

    Provides same interface as MCPServerPair but with lazy initialization.
    """

    def __init__(
        self,
        ga4_server: LazyMCPServer | None = None,
        gsc_server: LazyMCPServer | None = None,
        meta_ads_server: LazyMCPServer | None = None,
    ):
        self.ga4_server = ga4_server
        self.gsc_server = gsc_server
        self.meta_ads_server = meta_ads_server

    def get_all_servers(self) -> list[LazyMCPServer]:
        """Return all non-None servers."""
        return [s for s in [self.ga4_server, self.gsc_server, self.meta_ads_server] if s]

    async def cleanup_all(self) -> None:
        """Clean up all servers."""
        for server in self.get_all_servers():
            await server.cleanup()
