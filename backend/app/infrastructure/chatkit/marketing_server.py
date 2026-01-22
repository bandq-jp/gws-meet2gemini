from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import AsyncIterator, List

from agents import Runner, RunConfig
from openai import APIError, OpenAI
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
from openai.types.responses import ResponseInputTextParam, ResponseInputImageParam
from openai.types.responses.response_input_file_param import ResponseInputFileParam
from openai.types.responses.response_input_item_param import Message
import json
import os


class MarketingThreadItemConverter(ThreadItemConverter):
    """ThreadItem converter that is lenient to unknown item types (tool/workflow outputs)."""

    async def attachment_to_message_content(self, attachment):
        """Map uploaded attachments to Response content.

        OpenAI Responses `input_file` currently supports PDFs only; images use `input_image`.
        Other file types are exposed to Code Interpreter via container file_ids.
        """
        attachment_id = getattr(attachment, "id", None)
        if not attachment_id:
            raise ValueError("Attachment is missing id")

        # Check if the ID is already an OpenAI File ID (starts with 'file-')
        if attachment_id.startswith("file-"):
            openai_file_id = attachment_id
            logger.info(f"Attachment ID is already OpenAI file_id: {openai_file_id}")
        else:
            # Try to get file_id from attachment object
            openai_file_id = getattr(attachment, "file_id", None)

            # If not available, this is an error - upload should have set file_id
            if not openai_file_id:
                raise ValueError(
                    f"Attachment {attachment_id} missing file_id. "
                    "This indicates the upload did not complete successfully."
                )

            logger.info(f"Using OpenAI file_id={openai_file_id} for attachment {attachment_id}")

        mime_type = (getattr(attachment, "mime_type", None) or "").lower()
        name = getattr(attachment, "name", None) or attachment_id
        ext = os.path.splitext(name)[1].lower()

        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        if mime_type.startswith("image/") or ext in image_exts:
            return ResponseInputImageParam(
                type="input_image",
                file_id=openai_file_id,
                detail="auto",
            )

        if mime_type == "application/pdf" or ext == ".pdf":
            return ResponseInputFileParam(
                type="input_file",
                file_id=openai_file_id,
            )

        # Non-vision attachments: include a short textual note only.
        return ResponseInputTextParam(
            type="input_text",
            text=f"添付ファイル「{name}」を受け取りました。必要に応じて Code Interpreter で参照できます。",
        )

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
from app.infrastructure.chatkit.attachment_store import SupabaseAttachmentStore
from app.infrastructure.chatkit.context_manager import (
    create_trimming_filter,
    create_session_for_thread,
    LLMSummarizer,
    ContextBudget,
)
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class MarketingChatKitServer(ChatKitServer[MarketingRequestContext]):
    """ChatKit server wired to the SEO marketing agent runner.

    Implements multi-level context window management:
    - L1: ModelSettings.truncation="auto" (in agent factory)
    - L2: call_model_input_filter for custom trimming
    - L3: CompactionSessionWrapper for LLM-based compression
    - L4: TrimmingSession / SummarizingSession patterns
    """

    def __init__(
        self,
        store: Store[MarketingRequestContext],
        attachment_store: SupabaseAttachmentStore,
        agent_factory: MarketingAgentFactory,
        workflow_id: str,
        openai_client: OpenAI | None = None,
    ):
        super().__init__(store=store, attachment_store=attachment_store)
        self._agent_factory = agent_factory
        self._workflow_id = workflow_id or MARKETING_WORKFLOW_ID
        self._converter = MarketingThreadItemConverter()

        # Initialize OpenAI client for context summarization (L3/L4)
        settings = get_settings()
        self._openai_client = openai_client
        if self._openai_client is None and settings.openai_api_key:
            self._openai_client = OpenAI(api_key=settings.openai_api_key)

        # Initialize LLM summarizer for advanced context management
        self._summarizer: LLMSummarizer | None = None
        if self._openai_client and settings.context_session_type in ("summarizing", "compaction"):
            self._summarizer = LLMSummarizer(
                client=self._openai_client,
                model=settings.context_summarizer_model,
            )
            logger.info(
                f"LLM summarizer initialized with model={settings.context_summarizer_model}"
            )

        # Thread-local session cache for L3/L4 session-based management
        self._sessions: dict[str, any] = {}

    def _get_or_create_session(self, thread_id: str) -> any:
        """Get or create a context management session for a thread.

        This implements L3/L4 session-based context management.
        Session type is determined by CONTEXT_SESSION_TYPE setting:
        - "trimming": Fast, deterministic trimming (default)
        - "summarizing": LLM-based summarization for long contexts
        - "compaction": Hybrid approach with auto-compaction

        Args:
            thread_id: Thread/conversation ID

        Returns:
            Session instance (TrimmingSession, SummarizingSession, or CompactionSessionWrapper)
        """
        if thread_id in self._sessions:
            return self._sessions[thread_id]

        settings = get_settings()
        session = create_session_for_thread(
            thread_id=thread_id,
            session_type=settings.context_session_type,
            openai_client=self._openai_client,
            max_turns=settings.context_max_turns,
            max_items=settings.context_max_items,
            keep_last_n_turns=settings.context_keep_last_n_turns,
            context_limit=settings.context_summarization_trigger,
            compaction_threshold=settings.context_compaction_threshold,
            summarizer_model=settings.context_summarizer_model,
        )
        self._sessions[thread_id] = session
        logger.info(
            f"Created {settings.context_session_type} session for thread {thread_id}"
        )
        return session

    @staticmethod
    def _collect_code_interpreter_file_ids(items: List[ThreadItem]) -> list[str]:
        """Collect non-image attachment OpenAI file_ids for Code Interpreter."""
        file_ids: list[str] = []
        seen: set[str] = set()

        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

        for item in items:
            attachments = getattr(item, "attachments", None) or []
            for att in attachments:
                att_id = getattr(att, "id", "") or ""
                if att_id.startswith("file-"):
                    openai_id = att_id
                else:
                    openai_id = getattr(att, "file_id", None)
                if not openai_id or openai_id in seen:
                    continue

                mime = (getattr(att, "mime_type", None) or "").lower()
                name = getattr(att, "name", None) or att_id
                ext = os.path.splitext(name)[1].lower()
                if mime.startswith("image/") or ext in image_exts:
                    continue

                seen.add(openai_id)
                file_ids.append(openai_id)

        return file_ids

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
        ci_file_ids = self._collect_code_interpreter_file_ids(history_items)
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

        def mount_ci_files(target_agent) -> None:
            if not ci_file_ids:
                return
            applied = False
            for tool in getattr(target_agent, "tools", []) or []:
                if getattr(tool, "name", None) == "code_interpreter":
                    container = tool.tool_config.get("container")
                    if isinstance(container, dict) and container.get("type") == "auto":
                        container["file_ids"] = ci_file_ids
                    else:
                        tool.tool_config["container"] = {"type": "auto", "file_ids": ci_file_ids}
                    applied = True
            if applied:
                logger.info("Mounted %d file(s) into Code Interpreter container", len(ci_file_ids))
            else:
                logger.warning(
                    "Code Interpreter is disabled but %d attachment file(s) were uploaded",
                    len(ci_file_ids),
                )

        mount_ci_files(agent)

        # L2: Create context-aware RunConfig with call_model_input_filter
        settings = get_settings()
        context_filter = None
        if settings.context_management_enabled:
            context_filter = create_trimming_filter(
                max_turns=settings.context_max_turns,
                max_items=settings.context_max_items,
                clear_old_tool_results=settings.context_clear_old_tool_results,
                keep_recent_tool_results=settings.context_keep_recent_tool_results,
            )
            logger.info(
                f"Context management enabled: max_turns={settings.context_max_turns}, "
                f"max_items={settings.context_max_items}"
            )

        run_config = RunConfig(
            trace_metadata={
                "__trace_source__": "marketing-chatkit",
                "workflow_id": self._workflow_id,
                "user": context.user_email,
                "workflow_asset": asset_id,
            },
            call_model_input_filter=context_filter,  # L2: Apply context trimming filter
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
                # sandbox リンク書き換えは ToolUsageTracker が DB を直接更新するので、ここではそのまま流す
                yield event
        except APIError as exc:
            logger.exception("Marketing agent streaming failed")
            message = str(exc)
            error_source = self._infer_mcp_source(message)
            if error_source and self._is_mcp_toollist_error(message):
                label = self._format_mcp_label(error_source)
                yield ProgressUpdateEvent(
                    text=f"⚠️ {label}の初期化に失敗しました。該当ツールをスキップして続行します。"
                )
                fallback_agent = self._agent_factory.build_agent(
                    asset=asset, disabled_mcp_servers={error_source}
                )
                mount_ci_files(fallback_agent)
                fallback_result = Runner.run_streamed(
                    fallback_agent,
                    agent_input,
                    context=context_wrapper,
                    run_config=run_config,
                )
                fallback_monitored = instrument_run_result(fallback_result, tracker)
                async for event in stream_agent_response(context_wrapper, fallback_monitored):
                    yield event
            else:
                hint = (
                    "GA4連携の認証情報を再設定してください。"
                    if error_source == "ga4"
                    else "GSC連携の認証情報を再設定してください。"
                    if error_source == "gsc"
                    else "Meta広告連携の認証情報を再設定してください。"
                    if error_source == "meta_ads"
                    else "ツール連携の認証情報を確認してください。"
                )
                yield ProgressUpdateEvent(
                    text=(
                        f"⚠️ {error_source.upper() if error_source else '外部ツール'}"
                        f"の初期化に失敗しました。{hint}"
                    )
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
        server = MarketingChatKitServer._extract_mcp_server(message)
        if server:
            return server
        lowered = message.lower()
        if "ga4" in lowered:
            return "ga4"
        if "gsc" in lowered:
            return "gsc"
        if "meta_ads" in lowered or "meta-ads" in lowered or "meta ads" in lowered:
            return "meta_ads"
        if "ahrefs" in lowered:
            return "ahrefs"
        if "wordpress" in lowered:
            return "wordpress"
        if "achieve" in lowered:
            return "achieve"
        return None

    @staticmethod
    def _extract_mcp_server(message: str | None) -> str | None:
        if not message:
            return None
        match = re.search(r"mcp server: '([^']+)'", message, re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip().lower()

    @staticmethod
    def _is_mcp_toollist_error(message: str | None) -> bool:
        if not message:
            return False
        return "error retrieving tool list from mcp server" in message.lower()

    @staticmethod
    def _format_mcp_label(source: str) -> str:
        label = source.lower()
        if label == "ga4":
            return "GA4"
        if label == "gsc":
            return "GSC"
        if label == "meta_ads":
            return "Meta広告"
        if label == "ahrefs":
            return "Ahrefs"
        if label == "achieve":
            return "WordPress(achieve)"
        if label == "wordpress":
            return "WordPress"
        return source.upper()

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
    attachment_store = SupabaseAttachmentStore()
    agent_factory = MarketingAgentFactory(settings)
    if settings.openai_api_key:
        # Runner respects OPENAI_API_KEY env; set proactively when settings change
        import os

        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    return MarketingChatKitServer(
        store=store,
        attachment_store=attachment_store,
        agent_factory=agent_factory,
        workflow_id=settings.marketing_workflow_id,
    )
