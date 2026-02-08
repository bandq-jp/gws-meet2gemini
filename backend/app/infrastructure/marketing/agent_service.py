"""
Marketing Agent Service - Native OpenAI Agents SDK streaming.

Replaces ChatKit's stream_agent_response() with direct SDK event processing.
Uses Queue + pump task pattern from ga4-oauth-aiagent.

Optimizations:
- Simple query bypass: greetings and general questions skip orchestrator entirely
- Lazy MCP initialization: servers connect only when sub-agents are called
- CompactMCPServer: GA4 output compressed 76%

Chart Support:
- render_chart function tool for all agents to emit interactive charts
- Supports: line, bar, area, pie, donut, scatter, radar, funnel, table
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Any, AsyncGenerator

from agents import Runner, RunConfig, Agent, ModelSettings
from agents.items import ReasoningItem
from openai import AsyncOpenAI

from app.infrastructure.chatkit.keepalive import with_keepalive
from app.infrastructure.chatkit.mcp_manager import MCPSessionManager
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.marketing.chart_tools import MarketingChatContext, CHART_TOOLS

if TYPE_CHECKING:
    from agents.stream_events import StreamEvent

logger = logging.getLogger(__name__)

# Simple query patterns - skip orchestrator for these
# Use word boundaries (\b) to prevent partial matches (e.g., "hi" matching "hitocareer")
_SIMPLE_QUERY_PATTERNS = [
    r"^(こんにちは|こんばんは|おはよう|ありがとう|さようなら|はじめまして)(\s|$|！|。)",
    r"^(hello|hey|thanks|bye)(\s|$|!|\.)",  # Require word boundary
    r"^hi(\s|$|!)",  # "hi" only at start followed by space/end
    r"^(あなたは誰|あなたは何|何ができ|自己紹介|help|ヘルプ)",
    r"^(テスト|test)(\s|$)",
]
_SIMPLE_QUERY_COMPILED = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_QUERY_PATTERNS]

# Simple query response agent instructions (ultra-lightweight)
_SIMPLE_AGENT_INSTRUCTIONS = """b&qマーケティングAIです。短く応答してください。

挨拶には「こんにちは！マーケティング分析をお手伝いします。」程度で。
能力を聞かれたら「GA4分析、SEO分析、広告分析、CRMデータ分析ができます。」と1文で。

【重要】必ず1-2文以内で回答すること。"""

# Sentinel to signal end-of-stream from the SDK background task
_SENTINEL = object()


def _serialize_input_list(items: list) -> list[dict]:
    """Convert to_input_list() output into JSON-serializable dicts."""
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(item)
        elif hasattr(item, "model_dump"):
            result.append(item.model_dump(exclude_none=True))
        elif hasattr(item, "__dict__"):
            result.append({k: v for k, v in item.__dict__.items() if v is not None})
        else:
            # Fallback: try json round-trip
            try:
                result.append(json.loads(json.dumps(item, default=str)))
            except Exception:
                pass
    return result


class MarketingAgentService:
    """
    Service for streaming marketing agent responses.

    Replaces ChatKitServer.respond() with direct Agents SDK streaming.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        mcp_manager: MCPSessionManager | None = None,
    ):
        # Lazy import to avoid circular dependency
        from app.infrastructure.chatkit.agents import OrchestratorAgentFactory

        self._settings = settings or get_settings()
        self._mcp_manager = mcp_manager
        self._agent_factory = OrchestratorAgentFactory(self._settings)

    def _is_simple_query(self, message: str) -> bool:
        """
        Detect simple queries that don't need sub-agents.

        Simple queries include:
        - Greetings (こんにちは, hello)
        - Self-introduction requests (何ができますか)
        - Help requests
        - Test messages
        """
        message_clean = message.strip().lower()
        if len(message_clean) > 100:
            return False  # Long queries are not simple

        for pattern in _SIMPLE_QUERY_COMPILED:
            if pattern.search(message_clean):
                logger.info(f"[SimpleQuery] Detected simple query: {message[:30]}...")
                return True
        return False

    async def _stream_simple_response(
        self,
        message: str,
        conversation_id: str,
    ) -> AsyncGenerator[dict, None]:
        """
        Fast path for simple queries - no sub-agents, no MCP.

        Uses gpt-5-nano for ultra-fast responses (~0.5-1s).
        """
        logger.info("[SimpleQuery] Using fast path (no sub-agents)")

        simple_agent = Agent(
            name="SimpleResponder",
            instructions=_SIMPLE_AGENT_INSTRUCTIONS,
            model="gpt-5-nano",  # Ultra-fast model
            model_settings=ModelSettings(store=False),
            tools=[],  # No tools needed
        )

        result = Runner.run_streamed(
            simple_agent,
            input=[{"role": "user", "content": message}],
            max_turns=1,
        )

        try:
            async for event in result.stream_events():
                sdk_event = self._process_sdk_event(event)
                if sdk_event is not None:
                    yield sdk_event
        except Exception as e:
            yield {"type": "error", "message": str(e)}

        # Return context for continuation (simple queries don't preserve full context)
        yield {"type": "_context_items", "items": []}
        yield {"type": "done", "conversation_id": conversation_id}

    async def stream_chat(
        self,
        user_id: str,
        user_email: str,
        conversation_id: str,
        message: str,
        context_items: list[dict] | None = None,
        model_asset: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream chat response as SSE events.

        Yields events in the format:
        - {"type": "text_delta", "content": "..."}
        - {"type": "tool_call", "name": "...", "call_id": "..."}
        - {"type": "tool_result", "call_id": "...", "output": "..."}
        - {"type": "reasoning", "content": "..."}
        - {"type": "sub_agent_event", "agent": "...", "event_type": "..."}
        - {"type": "done", "conversation_id": "..."}
        """
        # FAST PATH: Simple queries bypass orchestrator entirely
        # This saves ~4 seconds for greetings and general questions
        if not context_items and self._is_simple_query(message):
            async for event in self._stream_simple_response(message, conversation_id):
                yield event
            return

        # Queue for multiplexing SDK events and out-of-band events
        queue: asyncio.Queue[dict | object] = asyncio.Queue()

        async def emit_event(event: dict) -> None:
            """Callback for tool functions to emit custom events."""
            await queue.put(event)

        # Create sub-agent stream callback
        # Receives AgentToolStreamEvent from SDK with keys: event, agent, tool_call
        async def on_sub_agent_stream(agent_tool_event: dict) -> None:
            """Capture sub-agent streaming events from Agent.as_tool()."""
            try:
                agent = agent_tool_event.get("agent")
                agent_name = getattr(agent, "name", "unknown") if agent else "unknown"
                stream_event = agent_tool_event.get("event")  # This is StreamEvent

                sse_event = self._process_sub_agent_event(agent_name, stream_event)
                if sse_event:
                    # Only log important events (not every raw_response_event)
                    event_type = sse_event.get("event_type", "")
                    if event_type in ("started", "tool_called", "reasoning", "message_output"):
                        logger.info(f"[Sub-agent] {agent_name}: {event_type}")
                    await queue.put(sse_event)
            except Exception as e:
                logger.exception(f"[Sub-agent] Error processing event: {e}")

        # Initialize lazy MCP servers (connect on-demand when sub-agent uses them)
        # This saves 2-3 seconds for simple queries that don't call sub-agents
        mcp_servers = []
        lazy_pair = None

        if self._mcp_manager and self._settings.use_local_mcp:
            lazy_pair = self._mcp_manager.create_lazy_server_pair()
            mcp_servers = lazy_pair.get_all_servers()
            # Note: Servers are NOT connected yet - they will connect on first use

        try:
            # Build orchestrator agent with sub-agent streaming
            agent = self._agent_factory.build_agent(
                asset=model_asset,
                mcp_servers=mcp_servers,
                on_sub_agent_stream=on_sub_agent_stream,
            )

            # Build input messages
            if context_items:
                input_messages = context_items + [{"role": "user", "content": message}]
            else:
                input_messages = [{"role": "user", "content": message}]

            # Create chat context
            chat_context = MarketingChatContext(
                emit_event=emit_event,
                user_id=user_id,
                user_email=user_email,
                conversation_id=conversation_id,
            )

            # Run agent in streaming mode
            run_config = RunConfig(
                trace_metadata={
                    "__trace_source__": "marketing-native",
                    "user": user_email,
                }
            )

            result = Runner.run_streamed(
                agent,
                input=input_messages,
                context=chat_context,
                run_config=run_config,
                max_turns=50,
            )

            async def _pump_sdk_events() -> None:
                """Background task: read SDK stream events and put into queue."""
                try:
                    async for event in result.stream_events():
                        sdk_event = self._process_sdk_event(event)
                        if sdk_event is not None:
                            await queue.put(sdk_event)
                except Exception as e:
                    await queue.put({"type": "error", "message": str(e)})
                finally:
                    await queue.put(_SENTINEL)

            pump_task = asyncio.create_task(_pump_sdk_events())

            try:
                while True:
                    # Use wait_for for keepalive
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=20.0)
                    except asyncio.TimeoutError:
                        # Send keepalive
                        yield {"type": "progress", "text": "処理中..."}
                        continue

                    if item is _SENTINEL:
                        break
                    yield item
            finally:
                if not pump_task.done():
                    pump_task.cancel()
                    try:
                        await pump_task
                    except (asyncio.CancelledError, Exception):
                        pass

            # Save context for next turn
            try:
                full_context = result.to_input_list()
                serialized = _serialize_input_list(full_context)
                yield {"type": "_context_items", "items": serialized}
            except Exception as e:
                logger.warning(f"Failed to serialize context_items: {e}")

            yield {"type": "done", "conversation_id": conversation_id}

        finally:
            # Cleanup lazy MCP servers (only cleans up servers that were actually connected)
            if lazy_pair:
                await lazy_pair.cleanup_all()

    def _process_sdk_event(self, event: "StreamEvent") -> dict | None:
        """Convert SDK stream event into SSE-compatible dict."""
        if event.type == "raw_response_event":
            data = event.data
            event_type = getattr(data, "type", "")

            if event_type == "response.output_text.delta":
                delta = getattr(data, "delta", "")
                if delta:
                    return {"type": "text_delta", "content": delta}

            elif event_type == "response.created":
                return {"type": "response_created"}

        elif event.type == "run_item_stream_event":
            item = event.item
            item_type = getattr(item, "type", "")

            if item_type == "tool_call_item":
                raw = item.raw_item
                return {
                    "type": "tool_call",
                    "call_id": getattr(raw, "call_id", None),
                    "name": getattr(raw, "name", "unknown"),
                    "arguments": getattr(raw, "arguments", ""),
                }

            elif item_type == "tool_call_output_item":
                raw = item.raw_item
                call_id = (
                    raw.get("call_id") if isinstance(raw, dict)
                    else getattr(raw, "call_id", None)
                )
                output = str(item.output)[:4000] if item.output else ""
                return {
                    "type": "tool_result",
                    "call_id": call_id,
                    "output": output,
                }

            # ReasoningItem handling
            if isinstance(item, ReasoningItem):
                return self._process_reasoning_item(item)

        elif event.type == "agent_updated_stream_event":
            new_agent = event.new_agent
            return {
                "type": "agent_updated",
                "agent": getattr(new_agent, "name", "unknown"),
            }

        return None

    def _process_sub_agent_event(
        self, agent_name: str, event: "StreamEvent"
    ) -> dict | None:
        """Convert sub-agent event to SSE event."""
        if event is None:
            return None

        event_type = getattr(event, "type", "")

        # Only log important events, not every raw_response_event
        if event_type != "raw_response_event":
            logger.debug(f"[Sub-agent] {agent_name}: event_type={event_type}")

        if event_type == "run_item_stream_event":
            item = event.item
            item_type = getattr(item, "type", "")
            event_name = getattr(event, "name", "")

            # Tool call from sub-agent
            if item_type == "tool_call_item":
                raw = item.raw_item
                return {
                    "type": "sub_agent_event",
                    "agent": agent_name,
                    "event_type": "tool_called",
                    "is_running": True,  # Sub-agent is still running
                    "data": {
                        "tool_name": getattr(raw, "name", "unknown"),
                        "call_id": getattr(raw, "call_id", None),
                    },
                }

            # Tool output from sub-agent
            elif item_type == "tool_call_output_item":
                raw = item.raw_item
                call_id = (
                    raw.get("call_id") if isinstance(raw, dict)
                    else getattr(raw, "call_id", None)
                )
                return {
                    "type": "sub_agent_event",
                    "agent": agent_name,
                    "event_type": "tool_output",
                    "is_running": True,  # Sub-agent is still running (processing output)
                    "data": {
                        "call_id": call_id,
                        "output_preview": str(item.output)[:200] if item.output else "",
                    },
                }

            # Reasoning from sub-agent
            if isinstance(item, ReasoningItem):
                summary = self._extract_reasoning_summary(item)
                return {
                    "type": "sub_agent_event",
                    "agent": agent_name,
                    "event_type": "reasoning",
                    "is_running": True,  # Sub-agent is still running (thinking)
                    "data": {
                        "content": summary or "分析中...",
                    },
                    # Mark for translation (same as main agent)
                    "_needs_translation": summary is not None,
                }

            # Message output from sub-agent (completion marker)
            if event_name == "message_output_created":
                return {
                    "type": "sub_agent_event",
                    "agent": agent_name,
                    "event_type": "message_output",
                    "is_running": False,  # Sub-agent completed
                    "data": {},
                }

        elif event_type == "raw_response_event":
            data = event.data
            inner_type = getattr(data, "type", "")

            # Sub-agent started (response created)
            if inner_type == "response.created":
                return {
                    "type": "sub_agent_event",
                    "agent": agent_name,
                    "event_type": "started",
                    "is_running": True,  # Sub-agent just started
                    "data": {},
                }

            # Note: We don't send text_delta for sub-agents
            # The sub-agent's output is returned to the orchestrator
            # which integrates it into the final response

        return None

    def _process_reasoning_item(self, item: ReasoningItem) -> dict:
        """Extract reasoning summary from ReasoningItem."""
        summary = self._extract_reasoning_summary(item)
        return {
            "type": "reasoning",
            "content": summary or "分析中...",
            "has_summary": summary is not None,
            "_needs_translation": summary is not None,  # Mark for translation
        }

    async def _translate_to_japanese(self, text: str) -> str:
        """Translate English reasoning summary to Japanese using GPT-5-nano."""
        try:
            client = AsyncOpenAI(api_key=self._settings.openai_api_key)
            response = await client.responses.create(
                model=self._settings.reasoning_translate_model,
                instructions=(
                    "Translate the following text to Japanese. "
                    "Output ONLY the translated text, nothing else. "
                    "Keep any markdown formatting intact."
                ),
                input=text,
                reasoning={"effort": "minimal", "summary": None},
                text={"verbosity": "low"},
                store=False,
            )
            return response.output_text or text
        except Exception as e:
            logger.warning(f"Reasoning summary translation failed, using original: {e}")
            return text

    def _extract_reasoning_summary(self, item: ReasoningItem) -> str | None:
        """Extract text from reasoning item summary."""
        if hasattr(item.raw_item, "summary") and item.raw_item.summary:
            texts = [
                s.text
                for s in item.raw_item.summary
                if hasattr(s, "text") and s.text
            ]
            if texts:
                return " ".join(texts)
        return None


# Singleton instance
_service_instance: MarketingAgentService | None = None
_adk_service_instance: "ADKAgentService | None" = None


def get_marketing_agent_service() -> "MarketingAgentService | ADKAgentService":
    """
    Get or create singleton agent service instance.

    Returns ADKAgentService if USE_ADK=true, otherwise MarketingAgentService (OpenAI SDK).
    """
    settings = get_settings()

    # --- ADK Mode ---
    if settings.use_adk:
        global _adk_service_instance
        if _adk_service_instance is None:
            # Initialize telemetry before creating the agent service
            if settings.adk_telemetry_enabled:
                from app.infrastructure.adk.telemetry.setup import setup_adk_telemetry
                setup_adk_telemetry(settings)

            from app.infrastructure.adk.agent_service import ADKAgentService
            _adk_service_instance = ADKAgentService(settings)
            logger.info("[ADK] Agent service initialized (model=%s)", settings.adk_orchestrator_model)
        return _adk_service_instance

    # --- OpenAI SDK Mode (default) ---
    global _service_instance
    if _service_instance is None:
        mcp_manager = None
        if settings.use_local_mcp:
            mcp_manager = MCPSessionManager(settings)
            logger.info(
                "Local MCP manager initialized (GA4=%s, GSC=%s)",
                settings.local_mcp_ga4_enabled,
                settings.local_mcp_gsc_enabled,
            )
        _service_instance = MarketingAgentService(
            settings=settings,
            mcp_manager=mcp_manager,
        )
    return _service_instance
