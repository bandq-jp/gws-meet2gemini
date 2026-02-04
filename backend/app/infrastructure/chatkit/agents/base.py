"""
Base class for Sub-Agent factories.

All sub-agents inherit from SubAgentFactory, which provides:
- Native tools (WebSearchTool, CodeInterpreterTool) for all agents
- Consistent model settings and configuration
- Abstract methods for domain-specific customization

Performance Optimizations:
- Native tools are cached at module level to avoid re-instantiation
- Each factory caches its built agent for reuse when MCP servers match
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING, Any, List

from agents import Agent, CodeInterpreterTool, ModelSettings, WebSearchTool
from openai.types.shared.reasoning import Reasoning

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

# Module-level cache for native tools (keyed by country setting)
_NATIVE_TOOLS_CACHE: dict[str, list[Any]] = {}


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
        """
        Model to use for this sub-agent. Configurable via SUB_AGENT_MODEL env.

        Supports:
        - OpenAI models: "gpt-5-mini", "gpt-5.1"
        - Gemini via LiteLLM: "litellm/gemini/gemini-3-flash-preview"
        """
        return self._settings.sub_agent_model

    @property
    def is_litellm_model(self) -> bool:
        """Check if the model is a LiteLLM model (non-OpenAI)."""
        return self.model.startswith("litellm/")

    @property
    def reasoning_effort(self) -> str:
        """Reasoning effort level. Low for sub-agents to optimize speed."""
        return "low"

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

        For OpenAI models (controlled by settings):
        - WebSearchTool: For real-time web search (default: enabled)
        - CodeInterpreterTool: For data analysis (default: DISABLED for sub-agents)
          Code Interpreter often causes wasteful "pass" calls when models
          mistakenly try to use it to call MCP tools.

        For LiteLLM models (Gemini, etc.):
        - These hosted tools are NOT supported (Responses API only)
        - Returns empty list

        Performance: Tools are cached at module level to avoid re-instantiation.
        """
        # WebSearchTool and CodeInterpreterTool are OpenAI Responses API features
        # They are not available via ChatCompletions API (LiteLLM/Gemini)
        if self.is_litellm_model:
            return []

        enable_web_search = self._settings.sub_agent_enable_web_search
        enable_code_interpreter = self._settings.sub_agent_enable_code_interpreter

        # Check cache first (key includes feature flags)
        cache_key = f"{self._settings.marketing_search_country}_{enable_web_search}_{enable_code_interpreter}"
        if cache_key in _NATIVE_TOOLS_CACHE:
            return _NATIVE_TOOLS_CACHE[cache_key]

        # Create and cache native tools based on settings
        tools: List[Any] = []

        if enable_web_search:
            tools.append(
                WebSearchTool(
                    search_context_size="medium",
                    user_location={
                        "country": self._settings.marketing_search_country,
                        "type": "approximate",
                    },
                )
            )

        if enable_code_interpreter:
            tools.append(
                CodeInterpreterTool(
                    tool_config={
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto",
                            "file_ids": [],
                        },
                    }
                )
            )

        _NATIVE_TOOLS_CACHE[cache_key] = tools
        logger.debug(f"[SubAgent] Native tools cached: key={cache_key}, tools={len(tools)}")
        return tools

    def _build_model_settings(self) -> ModelSettings:
        """
        Build model settings appropriate for the model type.

        OpenAI models: Full settings including reasoning
        LiteLLM models: Minimal settings (hosted features not supported)
        """
        if self.is_litellm_model:
            # LiteLLM/Gemini: Minimal settings
            # - store: Not supported via ChatCompletions API
            # - reasoning: LiteLLM handles mapping, but may not work for all models
            return ModelSettings()

        # OpenAI: Full settings with configurable reasoning
        # Note: verbosity is NOT a valid ModelSettings param - use instructions instead
        summary = "detailed" if self.reasoning_effort == "high" else "concise"
        return ModelSettings(
            store=True,
            parallel_tool_calls=True,  # Enable parallel tool execution
            reasoning=Reasoning(
                effort=self.reasoning_effort,  # Use property (default: "low")
                summary=summary,
            ),
        )

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
            model_settings=self._build_model_settings(),
            tool_use_behavior="run_llm_again",
        )
