"""
ADK Agent Service - Streaming handler for marketing AI.

Processes user messages through the ADK orchestrator and streams responses.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agents import OrchestratorAgentFactory
from .mcp_manager import ADKMCPManager

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class ADKAgentService:
    """
    Service for running ADK agents with streaming.

    Handles:
    - Agent initialization
    - Message processing
    - SSE event streaming
    - Session management
    """

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._session_service = InMemorySessionService()
        self._mcp_manager = ADKMCPManager(settings)
        self._orchestrator_factory = OrchestratorAgentFactory(settings)

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

        Args:
            user_id: Clerk user ID
            user_email: User email
            conversation_id: Optional conversation ID for session
            message: User message
            context_items: Previous conversation context
            model_asset: Model asset configuration

        Yields:
            SSE event dictionaries (not formatted strings)
        """
        async for sse_str in self.run_stream(
            message=message,
            conversation_id=conversation_id,
            context_items=context_items,
            asset=model_asset,
        ):
            # Parse SSE string back to dict for compatibility
            if sse_str.startswith("data: "):
                json_str = sse_str[6:].strip()
                if json_str:
                    try:
                        yield json.loads(json_str)
                    except json.JSONDecodeError:
                        pass

    async def _translate_to_japanese(self, text: str) -> str:
        """Translate English text to Japanese (stub for ADK)."""
        # ADK models typically respond in the instructed language
        # This is a stub for interface compatibility
        return text

    async def run_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        context_items: Optional[List[Dict[str, Any]]] = None,
        asset: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Run the orchestrator agent with streaming.

        Args:
            message: User message
            conversation_id: Optional conversation ID for session
            context_items: Previous conversation context
            asset: Model asset configuration

        Yields:
            SSE-formatted events
        """
        start_time = time.time()
        session_id = conversation_id or str(uuid.uuid4())

        # Create or get session (async in ADK)
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

        # Initialize MCP toolsets
        toolsets = await self._mcp_manager.create_toolsets()
        mcp_tools = toolsets.all()

        # Build orchestrator agent
        orchestrator = self._orchestrator_factory.build_agent(
            asset=asset,
            mcp_servers=mcp_tools,
        )

        # Create runner
        runner = Runner(
            agent=orchestrator,
            app_name="marketing_ai",
            session_service=self._session_service,
        )

        # Emit initial event
        yield self._format_sse({
            "type": "response_created",
            "conversation_id": session_id,
        })

        # Track text accumulation
        accumulated_text = ""
        activity_items: List[Dict[str, Any]] = []
        sequence = 0

        try:
            # Create user content (ADK requires Content object)
            user_content = types.Content(
                role="user",
                parts=[types.Part(text=message)],
            )

            # Run agent with streaming
            async for event in runner.run_async(
                user_id="default",
                session_id=session_id,
                new_message=user_content,
            ):
                sse_event = self._process_adk_event(event, sequence)
                if sse_event:
                    # Track activity items
                    if sse_event.get("type") == "text_delta":
                        accumulated_text += sse_event.get("content", "")
                    elif sse_event.get("type") in ("tool_call", "tool_result", "reasoning"):
                        activity_items.append({
                            "kind": sse_event["type"].replace("_", ""),
                            "sequence": sequence,
                            **sse_event,
                        })
                        sequence += 1

                    yield self._format_sse(sse_event)

        except Exception as e:
            logger.error(f"[ADK] Error during streaming: {e}")
            yield self._format_sse({
                "type": "error",
                "error": str(e),
            })

        # Emit done event
        elapsed = time.time() - start_time
        yield self._format_sse({
            "type": "done",
            "conversation_id": session_id,
            "elapsed_seconds": round(elapsed, 2),
            "final_text": accumulated_text,
        })

        # Emit context items for persistence
        context = session.state.get("context_items", [])
        if context:
            yield self._format_sse({
                "type": "_context_items",
                "context_items": context,
            })

        logger.info(f"[ADK] Stream completed in {elapsed:.2f}s")

    def _process_adk_event(self, event: Any, sequence: int) -> Optional[Dict[str, Any]]:
        """
        Convert ADK event to SSE event format.

        ADK events include:
        - content (text chunks)
        - function_call (tool calls)
        - function_response (tool results)
        - thinking (reasoning)
        """
        event_type = getattr(event, "type", None) or type(event).__name__

        # Text content
        if hasattr(event, "content") and event.content:
            if isinstance(event.content, str):
                return {
                    "type": "text_delta",
                    "content": event.content,
                    "sequence": sequence,
                }
            # Handle Content object
            if hasattr(event.content, "parts"):
                text_parts = []
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    return {
                        "type": "text_delta",
                        "content": "".join(text_parts),
                        "sequence": sequence,
                    }

        # Function call (tool invocation)
        if hasattr(event, "function_call") and event.function_call:
            fc = event.function_call
            return {
                "type": "tool_call",
                "tool_name": getattr(fc, "name", "unknown"),
                "tool_call_id": getattr(fc, "id", str(uuid.uuid4())),
                "arguments": getattr(fc, "args", {}),
                "sequence": sequence,
            }

        # Function response (tool result)
        if hasattr(event, "function_response") and event.function_response:
            fr = event.function_response
            output = getattr(fr, "response", {})
            if isinstance(output, dict):
                output_str = json.dumps(output, ensure_ascii=False)[:500]
            else:
                output_str = str(output)[:500]
            return {
                "type": "tool_result",
                "tool_name": getattr(fr, "name", "unknown"),
                "output": output_str,
                "sequence": sequence,
            }

        # Thinking/reasoning
        if hasattr(event, "thinking") or event_type == "thinking":
            thinking_text = getattr(event, "thinking", "") or getattr(event, "content", "")
            if thinking_text:
                return {
                    "type": "reasoning",
                    "content": thinking_text,
                    "sequence": sequence,
                }

        # Log unhandled event types for debugging
        logger.debug(f"[ADK] Unhandled event type: {event_type}")
        return None

    def _format_sse(self, data: Dict[str, Any]) -> str:
        """Format data as SSE event."""
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def create_adk_agent_service(settings: "Settings") -> ADKAgentService:
    """Factory function for ADK agent service."""
    return ADKAgentService(settings)
