from __future__ import annotations

import logging
from functools import lru_cache
from typing import AsyncIterator, List

from agents import Runner, RunConfig
from openai import APIError
from chatkit.agents import AgentContext, ThreadItemConverter, stream_agent_response
from chatkit.server import ChatKitServer
from chatkit.store import Store
from chatkit.types import (
    ProgressUpdateEvent,
    ThreadItem,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)
from openai.types.responses import ResponseInputTextParam
from openai.types.responses.response_input_item_param import Message
import json


class MarketingThreadItemConverter(ThreadItemConverter):
    """ThreadItem converter that is lenient to unknown item types (tool/workflow outputs)."""

    async def hidden_context_to_input(self, item):
        """Convert hidden context items (including tool calls and outputs) to model input."""
        logger.info(f"Converting HiddenContextItem to input: id={item.id}, content_preview={str(item.content)[:200]}")
        try:
            # Try to parse as JSON to see if it's a tool call or output
            content_data = json.loads(item.content) if isinstance(item.content, str) else item.content

            if not isinstance(content_data, dict):
                logger.warning(f"Hidden context content is not a dict, using default behavior")
                # Fall back to default behavior
                return await super().hidden_context_to_input(item)

            item_type = content_data.get("type")

            # Handle tool call
            if item_type == "tool_call":
                tool_name = content_data.get("tool_name", "Tool")
                arguments = content_data.get("arguments", {})
                description = content_data.get("description", "")

                # Format arguments for display
                args_str = ""
                if isinstance(arguments, dict) and arguments:
                    args_items = [f"{k}={v}" for k, v in list(arguments.items())[:3]]
                    args_str = f"\nArguments: {', '.join(args_items)}"
                    if len(arguments) > 3:
                        args_str += f" ... ({len(arguments)-3} more)"

                text = f"Tool Called: {tool_name}{args_str}"
                if description:
                    text += f"\nDescription: {description}"

                return Message(
                    type="message",
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=text,
                        )
                    ],
                )

            # Handle tool output
            elif item_type == "tool_output":
                tool_name = content_data.get("tool_name", "Tool")
                output = content_data.get("output", "")

                # Decode Unicode escape sequences for better readability
                # (e.g., \u3010 -> 【)
                if output and isinstance(output, str):
                    try:
                        # Try to parse as JSON and re-dump with ensure_ascii=False
                        parsed = json.loads(output)
                        output = json.dumps(parsed, ensure_ascii=False, indent=2)
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON or already decoded, keep as-is
                        pass

                # Smart truncation for extremely long outputs
                # Keep more data to preserve important information
                max_output_length = 100000  # 100K characters limit
                if len(output) > max_output_length:
                    # Keep first and last parts to preserve structure
                    keep_start = max_output_length // 2
                    keep_end = max_output_length // 2
                    output = (
                        output[:keep_start]
                        + f"\n\n... [省略: {len(output) - max_output_length} 文字] ...\n\n"
                        + output[-keep_end:]
                    )

                text = f"Tool Result: {tool_name}\nOutput: {output}"

                return Message(
                    type="message",
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=text,
                        )
                    ],
                )
        except (json.JSONDecodeError, TypeError):
            pass

        # Fall back to default behavior
        return await super().hidden_context_to_input(item)

    async def workflow_to_input(self, item):
        """Skip workflow items - we save tool outputs separately as hidden context."""
        # Return None to exclude workflow items from conversation history
        return None

    async def task_to_input(self, item):
        """Skip task items - we save tool outputs separately as hidden context."""
        # Return None to exclude task items from conversation history
        return None

    async def _thread_item_to_input_item(
        self,
        item: ThreadItem,
        is_last_message: bool = True,
    ) -> list:
        try:
            return await super()._thread_item_to_input_item(item, is_last_message)
        except Exception:
            # Fallback: stringify unknown item into user context so it isn't dropped
            dumped = {}
            try:
                dumped = item.model_dump(exclude_none=True)
            except Exception:
                try:
                    dumped = json.loads(json.dumps(item, default=str))
                except Exception:
                    dumped = {"type": str(getattr(item, "type", "unknown"))}

            return [
                Message(
                    type="message",
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=f"Previous tool/workflow output:\n{json.dumps(dumped, ensure_ascii=False)}",
                        )
                    ],
                )
            ]

from app.infrastructure.chatkit.context import MarketingRequestContext
from app.infrastructure.chatkit.tool_events import (
    ToolUsageTracker,
    instrument_run_result,
)
from app.infrastructure.chatkit.model_assets import (
    get_model_asset,
    set_thread_model_asset,
)
from app.infrastructure.chatkit.seo_agent_factory import (
    MARKETING_WORKFLOW_ID,
    MarketingAgentFactory,
)
from app.infrastructure.chatkit.supabase_store import SupabaseChatStore
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class MarketingChatKitServer(ChatKitServer[MarketingRequestContext]):
    """ChatKit server wired to the SEO marketing agent runner."""

    def __init__(
        self,
        store: Store[MarketingRequestContext],
        agent_factory: MarketingAgentFactory,
        workflow_id: str,
    ):
        super().__init__(store=store, attachment_store=None)
        self._agent_factory = agent_factory
        self._workflow_id = workflow_id or MARKETING_WORKFLOW_ID
        self._converter = MarketingThreadItemConverter()
    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: MarketingRequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        history_items = await self._load_full_history(thread.id, context)
        if input_user_message and (not history_items or history_items[-1].id != input_user_message.id):
            history_items.append(input_user_message)

        logger.info(f"Loaded {len(history_items)} history items for thread {thread.id}")
        item_types = [f"{item.type}({item.id[:8]}...)" for item in history_items]
        logger.info(f"Item types: {', '.join(item_types)}")

        agent_input = await self._converter.to_agent_input(history_items)
        metadata = thread.metadata or {}
        asset_id = context.model_asset_id or metadata.get("model_asset_id") or "standard"
        if context.model_asset_id and context.model_asset_id != metadata.get("model_asset_id"):
            try:
                set_thread_model_asset(thread.id, context.model_asset_id)
                metadata["model_asset_id"] = context.model_asset_id
            except Exception:
                logger.exception("Failed to persist model_asset_id on thread %s", thread.id)
        asset = get_model_asset(asset_id, context=context)
        if not asset:
            logger.warning("model asset %s not found; falling back to standard", asset_id)
            asset = get_model_asset("standard", context=context)
        agent = self._agent_factory.build_agent(asset=asset)
        run_config = RunConfig(
            trace_metadata={
                "__trace_source__": "marketing-chatkit",
                "workflow_id": self._workflow_id,
                "user": context.user_email,
                "workflow_asset": asset_id,
            }
        )

        yield ProgressUpdateEvent(text="📊 考え中…")

        context_wrapper = AgentContext(
            thread=thread,
            store=self.store,
            request_context=context,
        )

        tracker = ToolUsageTracker(context_wrapper)
        # Pass AgentContext into the run so function tools can access thread/store/user info
        result = Runner.run_streamed(
            agent,
            agent_input,
            context=context_wrapper,
            run_config=run_config,
        )
        monitored = instrument_run_result(result, tracker)

        try:
            async for event in stream_agent_response(context_wrapper, monitored):
                yield event
        except APIError as exc:
            logger.exception("Marketing agent streaming failed")
            error_source = self._infer_mcp_source(str(exc))
            hint = (
                "GA4連携の認証情報を再設定してください。"
                if error_source == "ga4"
                else "GSC連携の認証情報を再設定してください。"
                if error_source == "gsc"
                else "ツール連携の認証情報を確認してください。"
            )
            yield ProgressUpdateEvent(
                text=f"⚠️ {error_source.upper() if error_source else '外部ツール'}の初期化に失敗しました。{hint}"
            )
        except Exception:
            logger.exception("Unexpected marketing agent failure")
            yield ProgressUpdateEvent(
                text="⚠️ 内部エラーにより応答を完了できませんでした。時間をおいて再実行してください。"
            )
        finally:
            await tracker.close()

    @staticmethod
    def _infer_mcp_source(message: str | None) -> str | None:
        if not message:
            return None
        lowered = message.lower()
        if "ga4" in lowered:
            return "ga4"
        if "gsc" in lowered:
            return "gsc"
        if "ahrefs" in lowered:
            return "ahrefs"
        return None

    async def _load_full_history(
        self, thread_id: str, context: MarketingRequestContext
    ) -> List[ThreadItem]:
        items: List[ThreadItem] = []
        after: str | None = None
        attempts = 0
        while True:
            attempts += 1
            page = await self.store.load_thread_items(
                thread_id,
                after=after,
                limit=50,
                order="asc",
                context=context,
            )
            items.extend(page.data)
            if not page.has_more or not page.after:
                break
            after = page.after
            if attempts > 40:
                logger.warning("Thread %s history truncated for agent input", thread_id)
                break
        return items


@lru_cache(maxsize=1)
def get_marketing_chat_server() -> MarketingChatKitServer:
    settings = get_settings()
    store = SupabaseChatStore()
    agent_factory = MarketingAgentFactory(settings)
    if settings.openai_api_key:
        # Runner respects OPENAI_API_KEY env; set proactively when settings change
        import os

        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    return MarketingChatKitServer(
        store=store,
        agent_factory=agent_factory,
        workflow_id=settings.marketing_workflow_id,
    )
