"""
ADK Agent Service - Streaming handler for marketing AI (Google ADK version).

Processes user messages through the ADK orchestrator and streams responses.
Matches OpenAI Agents SDK functionality:
- Queue + pump task pattern for event multiplexing
- Chart rendering via emit_event callback
- Sub-agent event streaming with is_running tracking
- Reasoning/thinking events
- Translation of reasoning summaries to Japanese
- Simple query fast path
- Keepalive events
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Awaitable, Dict, List, Optional

from google.adk.agents import Agent
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner, RunConfig
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agents import OrchestratorAgentFactory
from .mcp_manager import ADKMCPManager

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

# Sentinel to signal end-of-stream
_SENTINEL = object()

# Simple query patterns - skip orchestrator for these
_SIMPLE_QUERY_PATTERNS = [
    r"^(こんにちは|こんばんは|おはよう|ありがとう|さようなら|はじめまして)(\s|$|！|。)",
    r"^(hello|hey|thanks|bye)(\s|$|!|\.)",
    r"^hi(\s|$|!)",
    r"^(あなたは誰|あなたは何|何ができ|自己紹介|help|ヘルプ)",
    r"^(テスト|test)(\s|$)",
]
_SIMPLE_QUERY_COMPILED = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_QUERY_PATTERNS]

# Simple query response agent instructions
_SIMPLE_AGENT_INSTRUCTIONS = """b&qマーケティングAIです。短く応答してください。

挨拶には「こんにちは！マーケティング分析をお手伝いします。」程度で。
能力を聞かれたら「GA4分析、SEO分析、広告分析、CRMデータ分析ができます。」と1文で。

【重要】必ず1-2文以内で回答すること。"""


@dataclass
class ADKChatContext:
    """Context passed to tool functions for event emission."""
    emit_event: Callable[[dict], Awaitable[None]]
    user_id: str
    user_email: str
    conversation_id: str


class ADKAgentService:
    """
    Service for running ADK agents with streaming.

    Handles:
    - Agent initialization
    - Message processing with Queue + pump task pattern
    - SSE event streaming
    - Session management
    - Chart rendering via emit_event
    - Sub-agent event streaming
    - Reasoning translation
    """

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._session_service = InMemorySessionService()
        self._mcp_manager = ADKMCPManager(settings)
        self._orchestrator_factory = OrchestratorAgentFactory(settings)

    def _is_simple_query(self, message: str) -> bool:
        """Detect simple queries that don't need sub-agents."""
        message_clean = message.strip().lower()
        if len(message_clean) > 100:
            return False

        for pattern in _SIMPLE_QUERY_COMPILED:
            if pattern.search(message_clean):
                logger.info(f"[ADK SimpleQuery] Detected: {message[:30]}...")
                return True
        return False

    def _normalize_agent_name(self, tool_name: str) -> str:
        """
        Normalize agent tool name to snake_case.

        Examples:
        - "ZohoCRMAgent" -> "zoho_crm"
        - "AnalyticsAgent" -> "analytics"
        - "AdPlatformAgent" -> "ad_platform"
        - "SEOAgent" -> "seo"
        - "WordPressAgent" -> "wordpress"
        - "CandidateInsightAgent" -> "candidate_insight"
        """
        # Remove "Agent" suffix
        name = tool_name.replace("Agent", "")

        # Special cases for acronyms
        name = name.replace("CRM", "Crm")
        name = name.replace("SEO", "Seo")

        # Convert CamelCase to snake_case
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())

        return "".join(result)

    async def _stream_simple_response(
        self,
        message: str,
        conversation_id: str,
    ) -> AsyncGenerator[dict, None]:
        """Fast path for simple queries using a lightweight ADK agent."""
        logger.info("[ADK SimpleQuery] Using fast path (no sub-agents)")

        try:
            # Create a simple agent for quick responses
            # Use the same model as the orchestrator
            simple_agent = Agent(
                name="SimpleResponder",
                model=self._settings.adk_orchestrator_model or "gemini-3-flash-preview",
                description="シンプルな応答用エージェント",
                instruction=_SIMPLE_AGENT_INSTRUCTIONS,
                tools=[],
            )

            # Create temporary session
            session_id = f"simple_{conversation_id}"
            session = await self._session_service.get_session(
                app_name="marketing_ai",
                user_id="default",
                session_id=session_id,
            )
            if session is None:
                session = await self._session_service.create_session(
                    app_name="marketing_ai",
                    user_id="default",
                    session_id=session_id,
                )

            runner = Runner(
                agent=simple_agent,
                app_name="marketing_ai",
                session_service=self._session_service,
            )

            user_content = types.Content(
                role="user",
                parts=[types.Part(text=message)],
            )

            # Enable SSE streaming mode
            run_config = RunConfig(streaming_mode=StreamingMode.SSE)
            async for event in runner.run_async(
                user_id="default",
                session_id=session_id,
                new_message=user_content,
                run_config=run_config,
            ):
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                yield {"type": "text_delta", "content": part.text}
                    elif isinstance(event.content, str):
                        yield {"type": "text_delta", "content": event.content}

        except Exception as e:
            logger.error(f"[ADK SimpleQuery] Error: {e}")
            yield {"type": "error", "message": str(e)}

        yield {"type": "_context_items", "items": []}
        yield {"type": "done", "conversation_id": conversation_id}

    async def stream_chat(
        self,
        user_id: str,
        user_email: str,
        conversation_id: Optional[str],
        message: str,
        context_items: Optional[List[Dict[str, Any]]] = None,
        model_asset: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat responses - interface compatible with OpenAI SDK service.

        Yields events in the format:
        - {"type": "text_delta", "content": "..."}
        - {"type": "tool_call", "name": "...", "call_id": "..."}
        - {"type": "tool_result", "call_id": "...", "output": "..."}
        - {"type": "reasoning", "content": "...", "_needs_translation": True}
        - {"type": "sub_agent_event", "agent": "...", "event_type": "..."}
        - {"type": "chart", "spec": {...}}
        - {"type": "progress", "text": "..."}
        - {"type": "done", "conversation_id": "..."}
        """
        session_id = conversation_id or str(uuid.uuid4())

        # FAST PATH: Simple queries bypass orchestrator entirely
        if not context_items and self._is_simple_query(message):
            async for event in self._stream_simple_response(message, session_id):
                yield event
            return

        # Queue for multiplexing SDK events and out-of-band events (chart, etc.)
        queue: asyncio.Queue[dict | object] = asyncio.Queue()

        async def emit_event(event: dict) -> None:
            """Callback for tool functions to emit custom events (charts, etc.)."""
            await queue.put(event)

        # Create chat context
        chat_context = ADKChatContext(
            emit_event=emit_event,
            user_id=user_id,
            user_email=user_email,
            conversation_id=session_id,
        )

        # Track sub-agent state
        sub_agent_states: Dict[str, dict] = {}

        # Initialize MCP toolsets
        mcp_toolsets = await self._mcp_manager.create_toolsets()

        try:
            # Create or get session
            session = await self._session_service.get_session(
                app_name="marketing_ai",
                user_id="default",
                session_id=session_id,
            )
            if session is None:
                session = await self._session_service.create_session(
                    app_name="marketing_ai",
                    user_id="default",
                    session_id=session_id,
                )

            # Build orchestrator agent with domain-specific MCP toolsets
            orchestrator = self._orchestrator_factory.build_agent(
                asset=model_asset,
                mcp_toolsets=mcp_toolsets,
            )

            # Create runner
            runner = Runner(
                agent=orchestrator,
                app_name="marketing_ai",
                session_service=self._session_service,
            )

            # Create user content
            user_content = types.Content(
                role="user",
                parts=[types.Part(text=message)],
            )

            # Emit initial event
            await queue.put({"type": "response_created"})

            # Track accumulated text for context and deduplication
            accumulated_text = ""
            sent_text_tracker: Dict[str, str] = {"text": ""}

            async def _pump_adk_events() -> None:
                """Background task: read ADK stream events and put into queue."""
                nonlocal accumulated_text
                try:
                    # Enable SSE streaming mode
                    run_config = RunConfig(streaming_mode=StreamingMode.SSE)
                    async for event in runner.run_async(
                        user_id="default",
                        session_id=session_id,
                        new_message=user_content,
                        run_config=run_config,
                    ):
                        sse_events = self._process_adk_event(
                            event, sub_agent_states, sent_text_tracker
                        )
                        if sse_events is not None:
                            for sse_event in sse_events:
                                # Track text for deduplication and context
                                if sse_event.get("type") == "text_delta":
                                    content = sse_event.get("content", "")
                                    accumulated_text += content
                                    sent_text_tracker["text"] += content
                                await queue.put(sse_event)
                except Exception as e:
                    logger.exception(f"[ADK] Error during streaming: {e}")
                    await queue.put({"type": "error", "message": str(e)})
                finally:
                    await queue.put(_SENTINEL)

            pump_task = asyncio.create_task(_pump_adk_events())

            try:
                while True:
                    # Use wait_for for keepalive (20 second timeout)
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

            # Return context for next turn
            yield {"type": "_context_items", "items": []}
            yield {"type": "done", "conversation_id": session_id}

        except Exception as e:
            logger.exception(f"[ADK] Error in stream_chat: {e}")
            yield {"type": "error", "message": str(e)}
            yield {"type": "done", "conversation_id": session_id}

    def _process_non_text_part(
        self,
        part: Any,
        sub_agent_states: Dict[str, dict],
    ) -> Optional[List[Dict[str, Any]]]:
        """Process non-text parts (function_call, function_response)."""
        results = []

        # Function response (tool result)
        if hasattr(part, "function_response") and part.function_response:
            fr = part.function_response
            tool_name = getattr(fr, "name", "unknown")
            output = getattr(fr, "response", {})

            if isinstance(output, dict) and output.get("_chart_spec"):
                results.append({
                    "type": "chart",
                    "spec": output["_chart_spec"],
                })
            elif tool_name.endswith("Agent"):
                agent_name = self._normalize_agent_name(tool_name)
                if agent_name in sub_agent_states:
                    sub_agent_states[agent_name]["is_running"] = False

                output_str = (
                    json.dumps(output, ensure_ascii=False)[:200]
                    if isinstance(output, dict)
                    else str(output)[:200]
                )
                results.append({
                    "type": "sub_agent_event",
                    "agent": agent_name,
                    "event_type": "message_output",
                    "is_running": False,
                    "data": {"output_preview": output_str},
                })
            else:
                output_str = (
                    json.dumps(output, ensure_ascii=False)[:4000]
                    if isinstance(output, dict)
                    else str(output)[:4000]
                )
                results.append({
                    "type": "tool_result",
                    "call_id": str(uuid.uuid4()),
                    "output": output_str,
                })

        # Function call (tool invocation)
        elif hasattr(part, "function_call") and part.function_call:
            fc = part.function_call
            tool_name = getattr(fc, "name", "unknown")

            if tool_name.endswith("Agent"):
                agent_name = self._normalize_agent_name(tool_name)
                sub_agent_states[agent_name] = {"is_running": True}
                results.append({
                    "type": "sub_agent_event",
                    "agent": agent_name,
                    "event_type": "started",
                    "is_running": True,
                    "data": {},
                })
            else:
                results.append({
                    "type": "tool_call",
                    "call_id": str(uuid.uuid4()),
                    "name": tool_name,
                    "arguments": json.dumps(getattr(fc, "args", {}), ensure_ascii=False),
                })

        return results if results else None

    def _process_adk_event(
        self,
        event: Any,
        sub_agent_states: Dict[str, dict],
        sent_text_tracker: Optional[Dict[str, str]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Convert ADK event to SSE event format.

        ADK events have content.parts[] which can contain:
        - text
        - function_call (with name attribute)
        - function_response (with name attribute)

        In SSE streaming mode:
        - partial=True: Streaming chunk (should be sent immediately)
        - partial=False: Final event with complete text (deduplicated against sent text)
        - partial=None: Non-streaming mode (send as-is)

        Returns a list of SSE events (since one ADK event can contain multiple parts).

        Args:
            sent_text_tracker: Optional dict with "text" key tracking all sent text.
                               Used for deduplication of partial=False events.
        """
        results = []

        # Check if this is a partial (streaming) event
        is_partial = getattr(event, "partial", None)

        # ADK events have content.parts[]
        if hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts"):
                # For partial=False (final) events, collect all text parts first for deduplication
                # This is necessary because Gemini may split the response into multiple parts
                if is_partial is False and sent_text_tracker is not None:
                    # Collect all text parts
                    all_text_parts = []
                    non_text_parts = []
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            all_text_parts.append(part.text)
                        else:
                            non_text_parts.append(part)

                    # Process non-text parts (function_call, function_response)
                    for part in non_text_parts:
                        part_result = self._process_non_text_part(
                            part, sub_agent_states
                        )
                        if part_result:
                            results.extend(part_result)

                    # Deduplicate concatenated text
                    if all_text_parts:
                        full_text = "".join(all_text_parts)
                        already_sent = sent_text_tracker.get("text", "")

                        if already_sent and full_text.startswith(already_sent):
                            # Only send the NEW portion
                            new_text = full_text[len(already_sent):]
                            if new_text:
                                logger.debug(f"[ADK] Sending new text from final event: {len(new_text)} chars")
                                results.append({
                                    "type": "text_delta",
                                    "content": new_text,
                                })
                            else:
                                logger.debug(f"[ADK] Skipping duplicate final text ({len(full_text)} chars)")
                        elif already_sent == full_text:
                            logger.debug(f"[ADK] Skipping exact duplicate final text")
                        elif not already_sent:
                            # No streaming events received - send full text
                            logger.debug(f"[ADK] No streaming text received, sending full final text")
                            results.append({
                                "type": "text_delta",
                                "content": full_text,
                            })
                        else:
                            # Text doesn't match - might be a different response format
                            logger.warning(f"[ADK] Final text doesn't match streamed text, sending full final text")
                            results.append({
                                "type": "text_delta",
                                "content": full_text,
                            })

                    return results if results else None

                # For partial=True or partial=None, process each part individually
                for part in event.content.parts:
                    # Use elif to ensure only one event type per part
                    # Priority: function_response > function_call > text

                    # --- Function response (tool result) - highest priority ---
                    if hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        tool_name = getattr(fr, "name", "unknown")
                        output = getattr(fr, "response", {})

                        # Check if this is a chart result
                        if isinstance(output, dict) and output.get("_chart_spec"):
                            chart_spec = output["_chart_spec"]
                            results.append({
                                "type": "chart",
                                "spec": chart_spec,
                            })
                        # Check if this is a sub-agent response
                        elif tool_name.endswith("Agent"):
                            agent_name = self._normalize_agent_name(tool_name)
                            if agent_name in sub_agent_states:
                                sub_agent_states[agent_name]["is_running"] = False

                            if isinstance(output, dict):
                                output_str = json.dumps(output, ensure_ascii=False)[:200]
                            else:
                                output_str = str(output)[:200]

                            results.append({
                                "type": "sub_agent_event",
                                "agent": agent_name,
                                "event_type": "message_output",
                                "is_running": False,
                                "data": {"output_preview": output_str},
                            })
                        else:
                            # Regular tool result
                            if isinstance(output, dict):
                                output_str = json.dumps(output, ensure_ascii=False)[:4000]
                            else:
                                output_str = str(output)[:4000]
                            results.append({
                                "type": "tool_result",
                                "call_id": str(uuid.uuid4()),
                                "output": output_str,
                            })

                    # --- Function call (tool invocation) ---
                    elif hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        tool_name = getattr(fc, "name", "unknown")

                        # Check if this is a sub-agent call (AgentTool)
                        if tool_name.endswith("Agent"):
                            # Extract agent name (e.g., "ZohoCRMAgent" -> "zoho_crm")
                            agent_name = self._normalize_agent_name(tool_name)
                            sub_agent_states[agent_name] = {"is_running": True}
                            results.append({
                                "type": "sub_agent_event",
                                "agent": agent_name,
                                "event_type": "started",
                                "is_running": True,
                                "data": {},
                            })
                        else:
                            # Regular tool call
                            results.append({
                                "type": "tool_call",
                                "call_id": str(uuid.uuid4()),
                                "name": tool_name,
                                "arguments": json.dumps(getattr(fc, "args", {}), ensure_ascii=False),
                            })

                    # --- Text content (lowest priority) ---
                    elif hasattr(part, "text") and part.text:
                        # For partial=True or partial=None, send text immediately
                        # (partial=False is handled separately above with concatenation)
                        results.append({
                            "type": "text_delta",
                            "content": part.text,
                        })

        # Return results if any, otherwise None
        return results if results else None

    async def _translate_to_japanese(self, text: str) -> str:
        """
        Translate English reasoning summary to Japanese.

        Note: In ADK mode with Gemini models, the orchestrator is instructed
        in Japanese, so reasoning summaries typically come back in Japanese.
        This method is kept for interface compatibility with OpenAI SDK version.
        """
        if not text:
            return text

        # Skip if already Japanese (simple heuristic - contains CJK characters)
        if any(ord(c) > 0x3000 for c in text[:50]):
            return text

        # For ADK mode, we return the original text since Gemini models
        # are instructed in Japanese and should respond in Japanese.
        # If translation is needed, it would require a separate API call.
        return text

    # Legacy method for backward compatibility
    async def run_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        context_items: Optional[List[Dict[str, Any]]] = None,
        asset: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Legacy method - wraps stream_chat for backward compatibility.

        Yields SSE-formatted strings.
        """
        async for event in self.stream_chat(
            user_id="default",
            user_email="default@example.com",
            conversation_id=conversation_id,
            message=message,
            context_items=context_items,
            model_asset=asset,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def create_adk_agent_service(settings: "Settings") -> ADKAgentService:
    """Factory function for ADK agent service."""
    return ADKAgentService(settings)
