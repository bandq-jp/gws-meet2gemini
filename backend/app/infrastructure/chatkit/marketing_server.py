from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import AsyncIterator, List

from agents import Runner, RunConfig
from openai import APIError
from chatkit.agents import AgentContext, simple_to_agent_input, stream_agent_response
from chatkit.server import ChatKitServer
from chatkit.store import Store
from chatkit.types import (
    ProgressUpdateEvent,
    ThreadItem,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)

from app.infrastructure.chatkit.context import MarketingRequestContext
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

    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: MarketingRequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        history_items = await self._load_full_history(thread.id, context)
        if input_user_message and (not history_items or history_items[-1].id != input_user_message.id):
            history_items.append(input_user_message)

        agent_input = await simple_to_agent_input(history_items)
        agent = self._agent_factory.build_agent()
        run_config = RunConfig(
            trace_metadata={
                "__trace_source__": "marketing-chatkit",
                "workflow_id": self._workflow_id,
                "user": context.user_email,
            }
        )

        yield ProgressUpdateEvent(text="📊 考え中…")

        context_wrapper = AgentContext(
            thread=thread,
            store=self.store,
            request_context=context,
        )

        result = Runner.run_streamed(agent, agent_input, run_config=run_config)

        try:
            async for event in stream_agent_response(context_wrapper, result):
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
