"""Marketing Agent Service — direct Agents SDK streaming without ChatKit.

Replaces MarketingChatKitServer with a simpler Queue-based SSE pattern
following the reference architecture (ga4-oauth-aiagent).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, AsyncGenerator, Awaitable, Callable

from agents import Runner, RunConfig, function_tool
from agents.items import ReasoningItem
from agents.tool_context import ToolContext
from openai import APIError, AsyncOpenAI
from openai.types.responses import ResponseInputImageParam, ResponseInputTextParam
from openai.types.responses.response_input_file_param import ResponseInputFileParam

from app.infrastructure.chatkit.ask_user_store import AskUserStore, ask_user_store
from app.infrastructure.chatkit.keepalive import with_keepalive
from app.infrastructure.chatkit.model_assets import get_model_asset
from app.infrastructure.chatkit.seo_agent_factory import (
    MARKETING_WORKFLOW_ID,
    MarketingAgentFactory,
)
from app.infrastructure.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Sentinel to signal end-of-stream from the SDK background task
_SENTINEL = object()

# Server-side tool types that execute within a single Response API call
# and do NOT produce ToolCallOutputItem from the SDK.
_SERVER_SIDE_TOOL_TYPES = frozenset({
    "web_search_call",
    "mcp_call",
    "code_interpreter_call",
    "file_search_call",
    "mcp_list_tools",
})


class _ErrorSentinel:
    """Carries an exception from the pump task so it can be re-raised
    in the queue consumer (e.g. APIError for MCP failover)."""

    def __init__(self, exc: Exception) -> None:
        self.exc = exc


# ---------- ChatContext (passed to tool functions via ToolContext) ----------

@dataclass
class ChatContext:
    """Custom context passed to tool functions via ToolContext[ChatContext]."""

    emit_event: Callable[[dict], Awaitable[None]]
    ask_user_store: AskUserStore
    conversation_id: str


# ---------- ask_user tool ----------

@function_tool
async def ask_user(
    ctx: ToolContext[ChatContext],
    questions: str,
) -> str:
    """ユーザーに構造化された質問を表示し、全回答をまとめて受け取る。

    Args:
        questions: 質問のJSON配列文字列。各要素は以下の形式:
            {"id": "一意ID", "question": "質問文（短文）", "type": "choice|text|confirm", "options": ["選択肢1", "選択肢2", ...]}
            - type="choice": optionsから1つ選択。必ずoptionsを指定すること
            - type="text": 自由テキスト入力
            - type="confirm": はい/いいえの確認
    """
    try:
        parsed = json.loads(questions)
        if not isinstance(parsed, list) or len(parsed) == 0:
            return "（質問の形式が不正です）"
    except json.JSONDecodeError:
        return "（質問のJSON解析に失敗しました）"

    store = ctx.context.ask_user_store
    group = store.create_question_group(parsed)

    # Build the SSE event with structured questions
    questions_data = [
        {
            "id": q.id,
            "question": q.question,
            "type": q.question_type,
            "options": q.options,
        }
        for q in group.questions
    ]

    await ctx.context.emit_event(
        {
            "type": "ask_user",
            "group_id": group.group_id,
            "questions": questions_data,
        }
    )

    try:
        await asyncio.wait_for(group.event.wait(), timeout=300)
    except asyncio.TimeoutError:
        store.cleanup(group.group_id)
        return "（ユーザーからの応答がタイムアウトしました）"

    responses = group.responses or {}
    store.cleanup(group.group_id)

    # Emit internal event so router can persist responses in activity_items
    await ctx.context.emit_event(
        {
            "type": "_ask_user_responses",
            "group_id": group.group_id,
            "responses": responses,
        }
    )

    # Return as readable text for the agent
    parts = []
    for q in group.questions:
        answer = responses.get(q.id, "").strip()
        if answer:
            parts.append(f"- {q.question}: {answer}")
        else:
            parts.append(f"- {q.question}: （スキップ — お任せ）")
    return "\n".join(parts)


# ---------- Helpers ----------

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
            result.append(json.loads(json.dumps(item, default=str)))
    return result


def build_attachment_content(
    openai_file_id: str, mime_type: str, name: str
) -> dict:
    """Build a Responses API content param for an attachment."""
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    ext = os.path.splitext(name)[1].lower()

    if mime_type.startswith("image/") or ext in image_exts:
        return {
            "type": "input_image",
            "file_id": openai_file_id,
            "detail": "auto",
        }
    if mime_type == "application/pdf" or ext == ".pdf":
        return {
            "type": "input_file",
            "file_id": openai_file_id,
        }
    return {
        "type": "input_text",
        "text": f"添付ファイル「{name}」を受け取りました。必要に応じて Code Interpreter で参照できます。",
    }


# ---------- Main Service ----------

class MarketingAgentService:
    """Streams agent responses as SSE-compatible dict events."""

    def __init__(self, agent_factory: MarketingAgentFactory, settings: Settings):
        self._agent_factory = agent_factory
        self._settings = settings

    async def stream_chat(
        self,
        *,
        user_email: str,
        message: str,
        model_asset_id: str = "standard",
        context_items: list[dict] | None = None,
        conversation_history: list[dict] | None = None,
        attachment_file_ids: list[str] | None = None,
        conversation_id: str = "",
    ) -> AsyncGenerator[dict, None]:
        """Stream agent response events.

        Yields dicts with ``type`` key: text_delta, response_created,
        tool_call, tool_result, reasoning, ask_user, keepalive,
        _context_items, _ask_user_responses, done, error.
        """
        asset = get_model_asset(model_asset_id) or get_model_asset("standard")
        agent = self._agent_factory.build_agent(asset=asset)

        # Add ask_user tool to agent's tools
        if agent.tools:
            agent.tools = list(agent.tools) + [ask_user]
        else:
            agent.tools = [ask_user]

        # Mount Code Interpreter file_ids if present
        if attachment_file_ids:
            self._mount_ci_files(agent, attachment_file_ids)

        # Build input
        if context_items:
            input_messages = context_items + [
                {"role": "user", "content": message}
            ]
        else:
            input_messages: list[dict] = []
            if conversation_history:
                input_messages.extend(conversation_history)
            input_messages.append({"role": "user", "content": message})

        run_config = RunConfig(
            trace_metadata={
                "__trace_source__": "marketing-chat",
                "workflow_id": self._settings.marketing_workflow_id or MARKETING_WORKFLOW_ID,
                "user": user_email,
                "workflow_asset": model_asset_id,
            }
        )

        try:
            async for event in self._run_with_failover(
                agent=agent,
                input_messages=input_messages,
                run_config=run_config,
                asset=asset,
                attachment_file_ids=attachment_file_ids,
                conversation_id=conversation_id,
            ):
                yield event
        except Exception:
            logger.exception("Unexpected marketing agent failure")
            yield {
                "type": "error",
                "message": "内部エラーにより応答を完了できませんでした。時間をおいて再実行してください。",
            }

    async def _run_with_failover(
        self,
        *,
        agent,
        input_messages: list,
        run_config: RunConfig,
        asset: dict[str, Any] | None,
        attachment_file_ids: list[str] | None,
        conversation_id: str = "",
    ) -> AsyncGenerator[dict, None]:
        """Run the agent with MCP failover logic."""
        try:
            async for event in self._run_streamed(
                agent, input_messages, run_config, conversation_id
            ):
                yield event
        except APIError as exc:
            logger.exception("Marketing agent streaming failed")
            message = str(exc)
            error_source = _infer_mcp_source(message)

            if error_source and _is_mcp_toollist_error(message):
                label = _format_mcp_label(error_source)
                yield {
                    "type": "keepalive",
                    "text": f"⚠️ {label}の初期化に失敗しました。該当ツールをスキップして続行します。",
                }

                fallback_agent = self._agent_factory.build_agent(
                    asset=asset, disabled_mcp_servers={error_source}
                )
                # Re-add ask_user tool to fallback agent
                if fallback_agent.tools:
                    fallback_agent.tools = list(fallback_agent.tools) + [ask_user]
                else:
                    fallback_agent.tools = [ask_user]

                if attachment_file_ids:
                    self._mount_ci_files(fallback_agent, attachment_file_ids)

                async for event in self._run_streamed(
                    fallback_agent, input_messages, run_config, conversation_id
                ):
                    yield event
            else:
                hint = {
                    "ga4": "GA4連携の認証情報を再設定してください。",
                    "gsc": "GSC連携の認証情報を再設定してください。",
                    "meta_ads": "Meta広告連携の認証情報を再設定してください。",
                }.get(error_source or "", "ツール連携の認証情報を確認してください。")
                src_label = error_source.upper() if error_source else "外部ツール"
                yield {
                    "type": "error",
                    "message": f"{src_label}の初期化に失敗しました。{hint}",
                }

    async def _run_streamed(
        self,
        agent,
        input_messages: list,
        run_config: RunConfig,
        conversation_id: str = "",
    ) -> AsyncGenerator[dict, None]:
        """Core streaming: Runner.run_streamed() → Queue → events.

        Queue is at service level so out-of-band events (ask_user, etc.)
        from tool functions can be multiplexed into the same stream.
        """
        # Queue for multiplexing SDK events and out-of-band tool events
        queue: asyncio.Queue[dict | object] = asyncio.Queue()

        async def emit_event(event: dict) -> None:
            """Callback passed to ChatContext — puts events into the queue."""
            await queue.put(event)

        chat_context = ChatContext(
            emit_event=emit_event,
            ask_user_store=ask_user_store,
            conversation_id=conversation_id,
        )

        result = Runner.run_streamed(
            agent,
            input=input_messages,
            run_config=run_config,
            context=chat_context,
            max_turns=50,
        )

        emitted_tool_ids: set[str] = set()

        async def _pump_sdk_events() -> None:
            try:
                async for event in result.stream_events():
                    for sdk_event in self._process_sdk_event(event, emitted_tool_ids):
                        await queue.put(sdk_event)
            except APIError as e:
                # Propagate APIError so _run_with_failover can catch it
                # and trigger MCP failover logic
                await queue.put(_ErrorSentinel(e))
            except Exception as e:
                await queue.put({"type": "error", "message": str(e)})
            finally:
                await queue.put(_SENTINEL)

        pump_task = asyncio.create_task(_pump_sdk_events())

        try:
            while True:
                item = await queue.get()
                if item is _SENTINEL:
                    break
                if isinstance(item, _ErrorSentinel):
                    raise item.exc
                yield item  # type: ignore[misc]
        finally:
            if not pump_task.done():
                pump_task.cancel()
                try:
                    await pump_task
                except (asyncio.CancelledError, Exception):
                    pass

        # Extract full conversation context for next turn
        try:
            full_context = result.to_input_list()
            serialized = _serialize_input_list(full_context)
            yield {"type": "_context_items", "items": serialized}
        except Exception as e:
            logger.warning(f"Failed to serialize context_items: {e}")

        # Signal stream completion
        yield {"type": "done"}

    def _process_sdk_event(self, event, emitted_tool_ids: set[str]) -> list[dict]:
        """Convert a single SDK stream event into SSE dicts.

        Returns a list (possibly empty) of dicts to emit.

        Server-side tools (WebSearch, CodeInterpreter, HostedMCP) execute
        within a single Responses API call.  The SDK emits
        ``run_item_stream_event(tool_call_item)`` only AFTER the full response
        step completes, and never emits ``tool_call_output_item`` for them.

        We therefore rely on two raw response events for correct timing:
        - ``response.output_item.added``  → emit ``tool_call`` when the tool starts
        - ``response.output_item.done``   → emit ``tool_result`` when it finishes

        For function tools (ask_user, Zoho CRM) the existing
        ``run_item_stream_event`` path still fires and is kept as-is.
        """
        results: list[dict] = []

        if event.type == "raw_response_event":
            data = event.data
            event_type = getattr(data, "type", "")

            if event_type == "response.output_text.delta":
                delta = getattr(data, "delta", "")
                if delta:
                    results.append({"type": "text_delta", "content": delta})

            elif event_type == "response.created":
                results.append({"type": "response_created"})

            elif event_type == "response.output_item.added":
                # Fires when a new output item is added to the response stream.
                # For server-side tools this arrives at the correct timing
                # (interleaved with text deltas).
                item = getattr(data, "item", None)
                if item:
                    item_type = getattr(item, "type", "")
                    item_id = getattr(item, "id", None)
                    if item_type in _SERVER_SIDE_TOOL_TYPES and item_id:
                        emitted_tool_ids.add(item_id)
                        name = getattr(item, "name", None) or item_type
                        arguments = getattr(item, "arguments", None) or ""
                        results.append({
                            "type": "tool_call",
                            "call_id": item_id,
                            "name": name,
                            "arguments": arguments,
                        })

            elif event_type == "response.output_item.done":
                # Fires when an output item completes.  For server-side tools
                # this signals that the tool finished execution.
                item = getattr(data, "item", None)
                if item:
                    item_id = getattr(item, "id", None)
                    item_type = getattr(item, "type", "")
                    if item_type in _SERVER_SIDE_TOOL_TYPES and item_id and item_id in emitted_tool_ids:
                        output = _extract_server_tool_output(item)
                        results.append({
                            "type": "tool_result",
                            "call_id": item_id,
                            "output": output,
                        })

        elif event.type == "run_item_stream_event":
            item = event.item
            if hasattr(item, "type"):
                if item.type == "tool_call_item":
                    raw = item.raw_item
                    raw_id = getattr(raw, "id", None)
                    # Skip if already emitted via raw response events
                    if raw_id and raw_id in emitted_tool_ids:
                        pass
                    else:
                        results.append({
                            "type": "tool_call",
                            "call_id": getattr(raw, "call_id", None) or raw_id,
                            "name": getattr(raw, "name", "unknown"),
                            "arguments": getattr(raw, "arguments", ""),
                        })
                elif item.type == "tool_call_output_item":
                    raw = item.raw_item
                    call_id = (
                        raw["call_id"]
                        if isinstance(raw, dict)
                        else getattr(raw, "call_id", None)
                    )
                    results.append({
                        "type": "tool_result",
                        "call_id": call_id,
                        "output": str(item.output)[:4000],
                    })
            if isinstance(item, ReasoningItem):
                results.append(self._process_reasoning_item(item))

        return results

    def _process_reasoning_item(self, item: ReasoningItem) -> dict:
        """Extract reasoning summary from a ReasoningItem."""
        summary_text = None
        if hasattr(item.raw_item, "summary") and item.raw_item.summary:
            texts = [
                s.text
                for s in item.raw_item.summary
                if hasattr(s, "text") and s.text
            ]
            if texts:
                summary_text = " ".join(texts)

        return {
            "type": "reasoning",
            "content": summary_text or "分析中...",
            "has_summary": summary_text is not None,
            "_needs_translation": summary_text is not None,
        }

    async def translate_to_japanese(self, text: str) -> str:
        """Translate English reasoning summary to Japanese using Responses API."""
        try:
            client = AsyncOpenAI(api_key=self._settings.openai_api_key)
            response = await client.responses.create(
                model="gpt-5-nano",
                instructions="Translate the following text to Japanese. Output ONLY the translated text, nothing else. Keep any markdown formatting intact.",
                input=text,
                reasoning={"effort": "minimal", "summary": None},
                text={"verbosity": "low"},
                store=False,
            )
            return response.output_text or text
        except Exception as e:
            logger.warning(f"Reasoning summary翻訳失敗、原文を使用: {e}")
            return text

    @staticmethod
    def _mount_ci_files(agent, file_ids: list[str]) -> None:
        """Mount file_ids into Code Interpreter container."""
        if not file_ids:
            return
        for tool in getattr(agent, "tools", []) or []:
            if getattr(tool, "name", None) == "code_interpreter":
                container = tool.tool_config.get("container")
                if isinstance(container, dict) and container.get("type") == "auto":
                    container["file_ids"] = file_ids
                else:
                    tool.tool_config["container"] = {
                        "type": "auto",
                        "file_ids": file_ids,
                    }
                logger.info(
                    "Mounted %d file(s) into Code Interpreter container",
                    len(file_ids),
                )
                return
        logger.warning(
            "Code Interpreter is disabled but %d attachment file(s) were uploaded",
            len(file_ids),
        )


# --- Server-side tool output extraction ---


def _extract_server_tool_output(item) -> str:
    """Extract a human-readable output summary from a completed server-side tool item."""
    item_type = getattr(item, "type", "")
    status = getattr(item, "status", "completed")

    if item_type == "web_search_call":
        return f"(web search {status})"
    elif item_type == "code_interpreter_call":
        # Code interpreter may have output/results
        output = getattr(item, "output", None)
        if output:
            return str(output)[:4000]
        return f"(code interpreter {status})"
    elif item_type == "mcp_call":
        output = getattr(item, "output", None)
        if output:
            return str(output)[:4000]
        return f"(mcp call {status})"
    elif item_type == "file_search_call":
        results = getattr(item, "results", None)
        if results:
            return str(results)[:4000]
        return f"(file search {status})"
    return f"({status})"


# --- MCP error helpers (ported from marketing_server.py) ---


def _infer_mcp_source(message: str | None) -> str | None:
    if not message:
        return None
    server = _extract_mcp_server(message)
    if server:
        return server
    lowered = message.lower()
    for key in ("ga4", "gsc", "meta_ads", "meta-ads", "meta ads", "ahrefs", "wordpress", "achieve"):
        if key in lowered:
            return key.replace("-", "_").replace(" ", "_")
    return None


def _extract_mcp_server(message: str | None) -> str | None:
    if not message:
        return None
    match = re.search(r"mcp server: '([^']+)'", message, re.IGNORECASE)
    return match.group(1).strip().lower() if match else None


def _is_mcp_toollist_error(message: str | None) -> bool:
    if not message:
        return False
    return "error retrieving tool list from mcp server" in message.lower()


def _format_mcp_label(source: str) -> str:
    labels = {
        "ga4": "GA4",
        "gsc": "GSC",
        "meta_ads": "Meta広告",
        "ahrefs": "Ahrefs",
        "achieve": "WordPress(achieve)",
        "wordpress": "WordPress",
    }
    return labels.get(source.lower(), source.upper())


# --- Factory function ---


@lru_cache(maxsize=1)
def get_marketing_agent_service() -> MarketingAgentService:
    settings = get_settings()
    agent_factory = MarketingAgentFactory(settings)
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    return MarketingAgentService(agent_factory=agent_factory, settings=settings)
