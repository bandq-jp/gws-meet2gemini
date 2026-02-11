"""
Base class for Sub-Agent factories (Google ADK version).

All sub-agents inherit from SubAgentFactory, which provides:
- Common configuration and model settings
- Abstract methods for domain-specific customization

This is the ADK-native implementation replacing the OpenAI Agents SDK version.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import FunctionTool
from google.genai import types

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class SubAgentFactory(ABC):
    """
    Base factory class for ADK sub-agents.

    Each sub-agent has:
    - Domain-specific tools (MCP or function tools)
    - Focused instructions for its domain
    - Gemini model (default: gemini-2.0-flash)
    """

    def __init__(self, settings: "Settings"):
        self._settings = settings

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Agent display name."""
        pass

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Tool name when exposed via AgentTool."""
        pass

    @property
    @abstractmethod
    def tool_description(self) -> str:
        """Tool description for orchestrator."""
        pass

    @property
    def model(self) -> str:
        """
        Model to use for this sub-agent.

        ADK supports:
        - Gemini models: "gemini-2.0-flash", "gemini-2.5-flash-preview-05-20"
        - Other models via LiteLLM integration
        """
        # Use Gemini Flash for sub-agents (fast and cost-effective)
        return self._settings.adk_sub_agent_model or "gemini-2.0-flash"

    @property
    def thinking_level(self) -> str:
        """Thinking level for this agent. Override in subclass for tuning.

        Options: minimal, low, medium, high
        Default: medium (balanced cost/quality for most agents)
        """
        return "medium"

    @abstractmethod
    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """
        Return domain-specific tools for this agent.

        Args:
            mcp_servers: MCP toolset instances
            asset: Model asset configuration

        Returns:
            List of tools (McpToolset, FunctionTool)
        """
        pass

    @abstractmethod
    def _build_instructions(self) -> str:
        """Build agent instructions focused on this domain."""
        pass

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """
        Build the sub-agent with domain tools.

        Args:
            mcp_servers: MCP toolset instances
            asset: Model asset configuration

        Returns:
            Configured ADK Agent instance
        """
        tools = self._get_domain_tools(mcp_servers, asset)

        return Agent(
            name=self.agent_name,
            model=self.model,
            description=self.tool_description,
            instruction=self._build_instructions(),
            tools=tools,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    thinking_level=self.thinking_level,
                ),
            ),
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )
