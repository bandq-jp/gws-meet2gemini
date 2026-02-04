"""
Base class for Sub-Agent factories.

All sub-agents inherit from SubAgentFactory, which provides:
- Native tools (WebSearchTool, CodeInterpreterTool) for all agents
- Consistent model settings and configuration
- Abstract methods for domain-specific customization
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List

from agents import Agent, CodeInterpreterTool, ModelSettings, WebSearchTool
from openai.types.shared.reasoning import Reasoning

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class SubAgentFactory(ABC):
    """
    Base factory class for sub-agents.

    Each sub-agent has:
    - Native tools (WebSearch, CodeInterpreter)
    - Domain-specific tools (MCP or function tools)
    - Focused instructions for its domain
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
        """Tool name when exposed via as_tool()."""
        pass

    @property
    @abstractmethod
    def tool_description(self) -> str:
        """Tool description for orchestrator."""
        pass

    @property
    def model(self) -> str:
        """Model to use for this sub-agent. Override for custom model."""
        return "gpt-5-mini"

    @property
    def reasoning_effort(self) -> str:
        """Reasoning effort level. Override for custom effort."""
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
            mcp_servers: Local MCP server instances (GA4, GSC, Meta Ads)
            asset: Model asset configuration

        Returns:
            List of tools (HostedMCPTool, FunctionTool, or MCP servers)
        """
        pass

    @abstractmethod
    def _build_instructions(self) -> str:
        """Build agent instructions focused on this domain."""
        pass

    def _get_native_tools(self) -> List[Any]:
        """
        Return native tools shared by all sub-agents.

        All sub-agents get:
        - WebSearchTool: For real-time web search
        - CodeInterpreterTool: For data analysis and visualization
        """
        return [
            WebSearchTool(
                search_context_size="medium",
                user_location={
                    "country": self._settings.marketing_search_country,
                    "type": "approximate",
                },
            ),
            CodeInterpreterTool(
                tool_config={
                    "type": "code_interpreter",
                    "container": {
                        "type": "auto",
                        "file_ids": [],
                    },
                }
            ),
        ]

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """
        Build the sub-agent with native and domain tools.

        Args:
            mcp_servers: Local MCP server instances
            asset: Model asset configuration

        Returns:
            Configured Agent instance
        """
        # Combine native tools + domain-specific tools
        tools = self._get_native_tools() + self._get_domain_tools(mcp_servers, asset)

        return Agent(
            name=self.agent_name,
            instructions=self._build_instructions(),
            tools=tools,
            model=self.model,
            model_settings=ModelSettings(
                store=True,
                reasoning=Reasoning(
                    effort=self.reasoning_effort,
                    summary="detailed",
                ),
                verbosity="medium",
            ),
            tool_use_behavior="run_llm_again",
        )
