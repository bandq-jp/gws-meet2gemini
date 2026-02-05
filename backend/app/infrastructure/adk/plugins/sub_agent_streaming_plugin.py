"""
Plugin to stream sub-agent internal events to the UI.

This plugin captures:
- Tool calls within sub-agents (GA4 API, Ahrefs, etc.)
- LLM reasoning from sub-agents
- Model responses within sub-agents

Events are forwarded to an async queue for SSE streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

if TYPE_CHECKING:
    from google.adk.agents.base_agent import BaseAgent
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


class SubAgentStreamingPlugin(BasePlugin):
    """
    Plugin that streams sub-agent internal events to the UI.

    When AgentTool runs a sub-agent with include_plugins=True (default),
    this plugin's callbacks are triggered for sub-agent tool calls and
    LLM interactions, allowing us to stream detailed progress to the UI.
    """

    # Agent names that are sub-agents (not the orchestrator)
    SUB_AGENT_NAMES = {
        "AnalyticsAgent",
        "AdPlatformAgent",
        "SEOAgent",
        "WordPressAgent",
        "ZohoCRMAgent",
        "CandidateInsightAgent",
    }

    def __init__(
        self,
        emit_callback: Callable[[Dict[str, Any]], Any],
        name: str = "sub_agent_streaming",
    ):
        """
        Initialize the plugin.

        Args:
            emit_callback: Async callable to emit events to the SSE queue.
                          Should accept a dict with event data.
            name: Plugin name.
        """
        super().__init__(name=name)
        self._emit_callback = emit_callback
        self._current_agent_stack: list[str] = []
        # Track pending tool calls for call_id matching
        # Key: (agent_name, tool_name) -> call_id
        self._pending_tool_calls: Dict[tuple, str] = {}

    def _normalize_agent_name(self, name: str) -> str:
        """Convert agent name to frontend format (e.g., 'AnalyticsAgent' -> 'analytics')."""
        if name.endswith("Agent"):
            name = name[:-5]  # Remove 'Agent' suffix
        # Convert CamelCase to snake_case
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result)

    def _is_sub_agent_context(self) -> bool:
        """Check if we're currently inside a sub-agent (not orchestrator)."""
        if not self._current_agent_stack:
            return False
        current = self._current_agent_stack[-1]
        return current in self.SUB_AGENT_NAMES

    def _get_current_agent(self) -> Optional[str]:
        """Get the current agent name (normalized for frontend)."""
        if not self._current_agent_stack:
            return None
        return self._normalize_agent_name(self._current_agent_stack[-1])

    async def _emit(self, event: Dict[str, Any]) -> None:
        """Emit an event to the SSE queue."""
        try:
            if asyncio.iscoroutinefunction(self._emit_callback):
                await self._emit_callback(event)
            else:
                self._emit_callback(event)
        except Exception as e:
            logger.warning(f"[Plugin] Failed to emit event: {e}")

    async def before_agent_callback(
        self,
        *,
        agent: BaseAgent,
        callback_context: CallbackContext,
    ) -> None:
        """Track when we enter an agent."""
        agent_name = agent.name
        self._current_agent_stack.append(agent_name)

        # If entering a sub-agent, emit a "started" event
        if agent_name in self.SUB_AGENT_NAMES:
            logger.debug(f"[Plugin] Entering sub-agent: {agent_name}")
            # Note: The orchestrator already emits "started" when calling AgentTool,
            # so we don't need to emit here.

    async def after_agent_callback(
        self,
        *,
        agent: BaseAgent,
        callback_context: CallbackContext,
    ) -> None:
        """Track when we exit an agent."""
        if self._current_agent_stack:
            self._current_agent_stack.pop()

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        """Emit event when a tool is called within a sub-agent."""
        if not self._is_sub_agent_context():
            return None

        agent_name = self._get_current_agent()
        tool_name = tool.name

        # Skip AgentTool calls (those are already tracked as sub_agent_event)
        if tool_name.endswith("Agent"):
            return None

        logger.debug(f"[Plugin] Sub-agent {agent_name} calling tool: {tool_name}")

        # Generate and track call_id for this tool call
        call_id = str(uuid.uuid4())
        self._pending_tool_calls[(agent_name, tool_name)] = call_id

        # Truncate arguments for display
        args_str = json.dumps(tool_args, ensure_ascii=False)
        if len(args_str) > 300:
            args_str = args_str[:300] + "..."

        await self._emit({
            "type": "sub_agent_event",
            "agent": agent_name,
            "event_type": "tool_called",
            "is_running": True,
            "data": {
                "call_id": call_id,
                "tool_name": tool_name,
                "arguments": args_str,
            },
        })

        return None  # Don't override tool behavior

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> Optional[dict]:
        """Emit event when a tool completes within a sub-agent."""
        if not self._is_sub_agent_context():
            return None

        agent_name = self._get_current_agent()
        tool_name = tool.name

        # Skip AgentTool calls
        if tool_name.endswith("Agent"):
            return None

        logger.debug(f"[Plugin] Sub-agent {agent_name} tool completed: {tool_name}")

        # Get the call_id we generated in before_tool_callback
        call_id = self._pending_tool_calls.pop((agent_name, tool_name), str(uuid.uuid4()))

        # Truncate result for display
        result_str = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "..."

        await self._emit({
            "type": "sub_agent_event",
            "agent": agent_name,
            "event_type": "tool_output",
            "is_running": True,
            "data": {
                "call_id": call_id,
                "tool_name": tool_name,
                "output_preview": result_str,
            },
        })

        return None  # Don't override result

    async def after_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> Optional[LlmResponse]:
        """Emit reasoning/thinking events from sub-agent LLM responses."""
        if not self._is_sub_agent_context():
            return None

        agent_name = self._get_current_agent()

        # Check for thinking/reasoning in the response
        if hasattr(llm_response, "content") and llm_response.content:
            parts = getattr(llm_response.content, "parts", [])
            for part in parts:
                # Check if this is a thought/reasoning part
                if hasattr(part, "thought") and part.thought:
                    text = getattr(part, "text", None)
                    if text:
                        logger.debug(f"[Plugin] Sub-agent {agent_name} reasoning: {text[:100]}...")
                        await self._emit({
                            "type": "sub_agent_event",
                            "agent": agent_name,
                            "event_type": "reasoning",
                            "is_running": True,
                            "data": {
                                "content": text,
                            },
                        })

        return None  # Don't override response

    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
    ) -> Optional[dict]:
        """Emit error events from sub-agent tool failures."""
        if not self._is_sub_agent_context():
            return None

        agent_name = self._get_current_agent()
        tool_name = tool.name

        logger.warning(f"[Plugin] Sub-agent {agent_name} tool error: {tool_name} - {error}")

        await self._emit({
            "type": "sub_agent_event",
            "agent": agent_name,
            "event_type": "tool_error",
            "is_running": True,
            "data": {
                "tool_name": tool_name,
                "error": str(error)[:300],
            },
        })

        return None  # Don't override error handling
