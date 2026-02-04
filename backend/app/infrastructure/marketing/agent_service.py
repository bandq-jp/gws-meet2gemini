"""
Marketing Agent Service - Native OpenAI Agents SDK streaming.

Replaces ChatKit's stream_agent_response() with direct SDK event processing.
Uses Queue + pump task pattern from ga4-oauth-aiagent.
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Awaitable

from agents import Runner, RunConfig
from agents.items import ReasoningItem
from openai import AsyncOpenAI

from app.infrastructure.chatkit.agents import OrchestratorAgentFactory
from app.infrastructure.chatkit.keepalive import with_keepalive
from app.infrastructure.chatkit.mcp_manager import MCPSessionManager
from app.infrastructure.config.settings import Settings, get_settings

if TYPE_CHECKING:
    from agents.stream_events import StreamEvent

logger = logging.getLogger(__name__)

# Sentinel to signal end-of-stream from the SDK background task
_SENTINEL = object()

# Keywords that indicate MCP tools are needed
_TOOL_KEYWORDS = {
    # Analytics (GA4/GSC)
    "ga4", "analytics", "traffic", "session", "pageview", "search console", "gsc",
    "index", "sitemap", "検索", "インデックス", "アクセス", "トラフィック", "pv", "ページビュー",
    # SEO (Ahrefs)
    "ahrefs", "backlink", "被リンク", "keyword", "キーワード", "競合", "competitor", "seo",
    "ドメインレーティング", "dr", "organic",
    # Ads (Meta)
    "meta", "facebook", "instagram", "広告", "キャンペーン", "campaign", "ad", "cpm", "cpc", "roas",
    # WordPress
    "wordpress", "記事", "article", "post", "ブログ", "blog", "投稿",
    # Zoho CRM
    "zoho", "crm", "求職者", "候補者", "candidate", "job seeker", "チャネル", "channel",
    "応募", "面接", "内定", "入社",
    # Candidate Insight
    "リスク", "risk", "緊急度", "urgency", "転職", "briefing", "ブリーフィング",
}


def _needs_mcp_tools(message: str) -> bool:
    """Check if the message likely needs MCP tools based on keywords."""
    lower = message.lower()
    return any(kw in lower for kw in _TOOL_KEYWORDS)


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


@dataclass
class MarketingChatContext:
    """Context passed to tool functions via ToolContext."""
    emit_event: Callable[[dict], Awaitable[None]]
    user_id: str
    user_email: str
    conversation_id: str


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
        self._settings = settings or get_settings()
        self._mcp_manager = mcp_manager
        self._agent_factory = OrchestratorAgentFactory(self._settings)

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

        # Initialize MCP servers (parallel for speed, skip for simple queries)
        mcp_servers = []
        mcp_stack = AsyncExitStack()

        # Check if MCP tools are likely needed based on query keywords
        needs_tools = _needs_mcp_tools(message)

        if self._mcp_manager and self._settings.use_local_mcp and needs_tools:
            try:
                pair = self._mcp_manager.create_server_pair()

                # Parallel initialization using asyncio.gather (saves ~2 seconds)
                async def init_server(server):
                    """Initialize single MCP server, returns server on success or None on failure."""
                    if server is None:
                        return None
                    try:
                        await mcp_stack.enter_async_context(server)
                        return server
                    except Exception as e:
                        logger.warning(f"[Local MCP] Server init failed: {e}")
                        return None

                results = await asyncio.gather(
                    init_server(pair.ga4_server),
                    init_server(pair.gsc_server),
                    init_server(pair.meta_ads_server),
                    return_exceptions=False,
                )
                mcp_servers = [s for s in results if s is not None]
                logger.info(f"[Local MCP] {len(mcp_servers)} servers initialized (parallel)")
            except Exception as e:
                logger.warning(f"[Local MCP] Init failed: {e}")
                mcp_servers = []
        elif self._mcp_manager and self._settings.use_local_mcp and not needs_tools:
            logger.info("[Local MCP] Skipped (simple query, no tool keywords detected)")

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
            # Cleanup MCP servers
            await mcp_stack.aclose()

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
                    "data": {
                        "content": summary or "分析中...",
                    },
                    # Mark for translation (same as main agent)
                    "_needs_translation": summary is not None,
                }

            # Message output from sub-agent
            if event_name == "message_output_created":
                return {
                    "type": "sub_agent_event",
                    "agent": agent_name,
                    "event_type": "message_output",
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


def get_marketing_agent_service() -> MarketingAgentService:
    """Get or create singleton MarketingAgentService instance."""
    global _service_instance
    if _service_instance is None:
        settings = get_settings()
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
