from __future__ import annotations

import asyncio
import json
import logging
import uuid
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional, Tuple

from agents.stream_events import RunItemStreamEvent, StreamEvent
from chatkit.agents import AgentContext
from chatkit.types import (
    CustomTask,
    HiddenContextItem,
    ThreadItemUpdated,
    ThreadItemReplacedEvent,
    WorkflowItem,
    WorkflowTaskAdded,
    WorkflowTaskUpdated,
    AssistantMessageItem,
)
from app.infrastructure.config.settings import get_settings
from app.infrastructure.security.marketing_token_service import MarketingTokenService
logger = logging.getLogger(__name__)
SANDBOX_LINK_RE = re.compile(r"\[([^\]]+)\]\((sandbox:/[^\)]+)\)")


@dataclass
class TaskRef:
    task: CustomTask
    index: int
    identifiers: set[str] = field(default_factory=set)


class ToolWorkflowPresenter:
    def __init__(self, ctx: AgentContext[Any]):
        self._ctx = ctx
        self._workflow_item: WorkflowItem | None = None
        self._lookup: Dict[str, TaskRef] = {}

    async def add_tool(
        self,
        *,
        identifiers: Iterable[str],
        title: str,
        icon: str,
        description: str | None,
    ) -> None:
        workflow_item = await self._ensure_reasoning_workflow()
        if not workflow_item:
            return
        task = CustomTask(
            title=title,
            icon=icon,
            content=description,
            status_indicator="loading",
        )
        workflow_item.workflow.tasks.append(task)
        position = len(workflow_item.workflow.tasks) - 1
        await self._ctx.stream(
            ThreadItemUpdated(
                item_id=workflow_item.id,
                update=WorkflowTaskAdded(task=task, task_index=position),
            )
        )
        ref = TaskRef(task=task, index=position, identifiers=set(identifiers))
        for ident in ref.identifiers:
            self._lookup[ident] = ref

    async def complete_tool(self, identifier: str, summary: str | None) -> None:
        workflow_item = await self._ensure_reasoning_workflow()
        if not workflow_item:
            return
        ref = self._lookup.get(identifier)
        if not ref:
            return
        ref.task.status_indicator = "complete"
        if summary:
            base = (ref.task.content or "").strip()
            ref.task.content = f"{base}\n結果: {summary}" if base else summary
        await self._ctx.stream(
            ThreadItemUpdated(
                item_id=workflow_item.id,
                update=WorkflowTaskUpdated(task=ref.task, task_index=ref.index),
            )
        )
        for ident in list(ref.identifiers):
            self._lookup.pop(ident, None)

    async def close(self) -> None:
        self._workflow_item = None
        self._lookup.clear()

    async def _ensure_reasoning_workflow(self) -> WorkflowItem | None:
        if self._workflow_item and self._workflow_item.workflow.type == "reasoning":
            return self._workflow_item
        for _ in range(80):
            candidate = self._ctx.workflow_item
            if candidate and candidate.workflow.type == "reasoning":
                self._workflow_item = candidate
                return candidate
            await asyncio.sleep(0.05)
        return None


class InstrumentedRunResult:
    def __init__(
        self,
        original,
        observer: Callable[[StreamEvent], Awaitable[None]],
    ) -> None:
        self._original = original
        self._observer = observer

    async def stream_events(self):
        async for event in self._original.stream_events():
            await self._observer(event)
            yield event

    def __getattr__(self, item):
        return getattr(self._original, item)


class ToolUsageTracker:
    def __init__(self, ctx: AgentContext[Any]):
        self._presenter = ToolWorkflowPresenter(ctx)
        self._ctx = ctx
        self._tool_calls: Dict[str, Dict[str, Any]] = {}
        # filename / basename -> (container_id, file_id)
        self._container_files: Dict[str, Tuple[str, str]] = {}
        # file_id -> container_id
        self._file_to_container: Dict[str, str] = {}
        self._token_service: MarketingTokenService | None = None
        # collected attachments for the current assistant message
        self._attachments: list[dict[str, str | None]] = []

    async def observe(self, event: StreamEvent) -> None:
        # Log all events for debugging
        logger.debug(f"Received event: type={type(event).__name__}, name={getattr(event, 'name', 'N/A')}")

        if not isinstance(event, RunItemStreamEvent):
            return

        # Log RunItemStreamEvent details
        logger.debug(f"RunItemStreamEvent: name={event.name}, item={type(event.item).__name__ if hasattr(event, 'item') else 'N/A'}")

        if event.name == "tool_called":
            # Debug logging to see what's coming through
            raw_item = event.item.raw_item
            tool_type = self._get_field(raw_item, "type")

            # Check if output is already available (MCP calls often complete immediately)
            output = self._get_field(raw_item, "output")
            has_output = output is not None
            logger.info(f"Tool called event: type={tool_type}, has_output={has_output}")

            metadata = self._describe_tool_call(raw_item)
            if metadata:
                # Store tool call metadata for later association with output
                identifier = self._extract_identifier(raw_item)
                if identifier:
                    self._tool_calls[identifier] = {
                        "title": metadata["title"],
                        "description": metadata["description"],
                        "raw_item": raw_item,
                    }
                    logger.info(f"Storing tool call: identifier={identifier}, title={metadata['title']}")
                await self._presenter.add_tool(**metadata)

                # Save tool call as hidden context for conversation history
                await self._save_tool_call_as_context(identifier, event.item, metadata)

                # If output is already available, save it immediately
                if has_output and identifier:
                    logger.info(f"Tool output already available for {identifier}, saving immediately")
                    # Create a mock output item with the output data
                    class OutputItem:
                        def __init__(self, raw_item, output):
                            self.raw_item = raw_item
                            self.output = output

                    output_item = OutputItem(raw_item, output)
                    summary = self._summarize_output(output)
                    await self._presenter.complete_tool(identifier, summary)
                    await self._save_tool_output_as_context(identifier, output_item)
            else:
                logger.warning(f"No metadata for tool call: type={tool_type}")
        elif event.name == "tool_output":
            identifier = self._extract_identifier(event.item.raw_item)
            tool_type = self._get_field(event.item.raw_item, "type")
            logger.info(f"Tool output event: identifier={identifier}, type={tool_type}")
            logger.debug(f"Tool output raw_item: {event.item.raw_item}")

            # File annotations for Code Interpreter outputs are handled in
            # `message_output_created` where container_file_citation is present.
            if tool_type == "code_interpreter_call":
                logger.debug("Code Interpreter output observed; waiting for message_output_created for file citations")

            if identifier:
                summary = self._summarize_output(event.item.output)
                await self._presenter.complete_tool(identifier, summary)

                # Save tool output as hidden context for conversation history
                await self._save_tool_output_as_context(identifier, event.item)
        elif event.name == "message_output_created":
            # This event contains the final output including Code Interpreter results
            logger.info(f"Message output created event")
            logger.debug(f"Message output item: {event.item}")
            self._attachments.clear()

            # Extract file annotations from the message content
            if hasattr(event.item, "raw_item"):
                raw_item = event.item.raw_item
                logger.debug(f"Message output raw_item: {raw_item}")
                # Responses API sometimes populates `output`/`outputs`, and sometimes only `content` on the message.
                outputs = (
                    getattr(raw_item, "output", None)
                    or getattr(raw_item, "outputs", None)
                    or []
                )

                # Always also look at top-level content for annotations.
                top_level_content = getattr(raw_item, "content", None)

                if not isinstance(outputs, list):
                    outputs = [outputs]

                logger.debug("message_output_created outputs len=%s", len(outputs))

                self._extract_container_files_from_outputs(outputs)
                if top_level_content:
                    self._extract_container_files_from_content_blocks(top_level_content)

                # After registering container files, rewrite links and attach metadata
                await self._rewrite_assistant_message_links(raw_item)
                await self._attach_container_file_metadata(raw_item)
        else:
            # Log other event names
            logger.debug(f"Unhandled RunItemStreamEvent: name={event.name}")

    async def _save_tool_call_as_context(
        self, identifier: str, tool_call_item: Any, metadata: dict[str, Any]
    ) -> None:
        """Save tool call as a hidden context item for conversation history."""
        try:
            raw_item = tool_call_item.raw_item

            # Extract arguments
            arguments = self._get_field(raw_item, "arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    pass

            # Create hidden context content for tool call
            context_content = {
                "type": "tool_call",
                "tool_call_id": identifier,
                "tool_name": metadata.get("title", "Tool"),
                "tool_type": self._get_field(raw_item, "type"),
                "arguments": arguments,
                "description": metadata.get("description"),
                "timestamp": datetime.now().isoformat(),
            }

            # Create and save HiddenContextItem
            # Use custom ID generation since "context" is not in ChatKit's _ID_PREFIXES
            hidden_item = HiddenContextItem(
                id=f"ctx_{uuid.uuid4().hex[:8]}",
                thread_id=self._ctx.thread.id,
                created_at=datetime.now(),
                content=json.dumps(context_content, ensure_ascii=False),
            )

            await self._ctx.store.add_thread_item(
                self._ctx.thread.id,
                hidden_item,
                self._ctx.request_context,
            )
            logger.info(f"Successfully saved tool call context: id={hidden_item.id}, tool={context_content.get('tool_name')}")
        except Exception as e:
            # Don't fail the entire stream if context saving fails
            logger.exception(f"Failed to save tool call context: {e}")
            pass

    async def _save_tool_output_as_context(
        self, identifier: str, tool_output_item: Any
    ) -> None:
        """Save tool output as a hidden context item for conversation history."""
        try:
            tool_call = self._tool_calls.get(identifier, {})
            tool_title = tool_call.get("title", "Tool")
            output = tool_output_item.output

            # Format the output
            if output is None:
                output_text = "No output"
            elif isinstance(output, str):
                output_text = output
            else:
                try:
                    output_text = json.dumps(output, ensure_ascii=False, indent=2)
                except TypeError:
                    output_text = str(output)

            # Create hidden context content
            context_content = {
                "type": "tool_output",
                "tool_call_id": identifier,
                "tool_name": tool_title,
                "output": output_text,
                "timestamp": datetime.now().isoformat(),
            }

            # Create and save HiddenContextItem
            # Use custom ID generation since "context" is not in ChatKit's _ID_PREFIXES
            hidden_item = HiddenContextItem(
                id=f"ctx_{uuid.uuid4().hex[:8]}",
                thread_id=self._ctx.thread.id,
                created_at=datetime.now(),
                content=json.dumps(context_content, ensure_ascii=False),
            )

            await self._ctx.store.add_thread_item(
                self._ctx.thread.id,
                hidden_item,
                self._ctx.request_context,
            )
            logger.info(f"Successfully saved tool output context: id={hidden_item.id}, tool={tool_title}")

            # Clean up stored tool call
            self._tool_calls.pop(identifier, None)
        except Exception as e:
            # Don't fail the entire stream if context saving fails
            logger.exception(f"Failed to save tool output context: {e}")
            pass

    async def close(self) -> None:
        await self._presenter.close()
        self._tool_calls.clear()
        self._container_files.clear()
        self._file_to_container.clear()
        self._attachments.clear()

    def _register_container_file(
        self, *, filename: str | None, file_id: str, container_id: str
    ) -> None:
        """Register a container/file mapping for later sandbox link rewrites."""
        self._file_to_container[file_id] = container_id

        # Canonical keys we want to match against: full filename, basename, /mnt/data/{basename}, sandbox:/mnt/data/{basename}
        keys: list[str] = []
        if filename:
            keys.append(filename)
            basename = filename.split("/")[-1]
            keys.append(basename)
            keys.append(f"/mnt/data/{basename}")
            keys.append(f"sandbox:/mnt/data/{basename}")
        else:
            logger.info(
                "Registered container file without filename: file_id=%s, container_id=%s",
                file_id,
                container_id,
            )
        for key in keys:
            self._container_files[key] = (container_id, file_id)
        if keys:
            logger.info(
                "Registered container file: keys=%s, file_id=%s, container_id=%s",
                keys,
                file_id,
                container_id,
            )

    def lookup_container_file(self, path_or_name: str) -> tuple[str, str] | None:
        """
        Resolve sandbox path or filename to (container_id, file_id).
        - Checks exact key
        - Falls back to basename
        """
        if not path_or_name:
            return None
        normalized = path_or_name
        if normalized.startswith("sandbox:"):
            normalized = normalized.replace("sandbox:", "", 1)
        basename = normalized.split("/")[-1]
        return (
            self._container_files.get(path_or_name)
            or self._container_files.get(normalized)
            or self._container_files.get(basename)
            or self._container_files.get(f"/mnt/data/{basename}")
            or self._container_files.get(f"sandbox:/mnt/data/{basename}")
        )

    # --- internal helpers -------------------------------------------------

    def _extract_container_files_from_outputs(self, outputs: list[Any]) -> None:
        for output in outputs:
            output_dict = output
            if hasattr(output, "model_dump"):
                try:
                    output_dict = output.model_dump()
                except Exception:
                    output_dict = output
            if not isinstance(output_dict, dict):
                output_dict = getattr(output, "__dict__", {}) or {}

            output_type = output_dict.get("type") or getattr(output, "type", None)
            if output_type != "output_text":
                continue

            content_items = output_dict.get("content") or getattr(output, "content", []) or []
            self._extract_container_files_from_content_blocks(content_items)

    def _extract_container_files_from_content_blocks(self, content_items: Any) -> None:
        if not isinstance(content_items, list):
            content_items = [content_items]

        for content_item in content_items:
            content_dict = content_item
            if hasattr(content_item, "model_dump"):
                try:
                    content_dict = content_item.model_dump()
                except Exception:
                    content_dict = content_item
            if not isinstance(content_dict, dict):
                content_dict = getattr(content_item, "__dict__", {}) or {}

            annotations = content_dict.get("annotations") or getattr(content_item, "annotations", []) or []
            if not annotations:
                continue

            logger.debug("Found %s annotations on output content", len(annotations))

            for annotation in annotations:
                ann_dict = annotation
                if hasattr(annotation, "model_dump"):
                    try:
                        ann_dict = annotation.model_dump()
                    except Exception:
                        ann_dict = annotation
                if not isinstance(ann_dict, dict):
                    ann_dict = getattr(annotation, "__dict__", {}) or {}

                ann_type = ann_dict.get("type") or getattr(annotation, "type", None)
                if ann_type != "container_file_citation":
                    continue

                container_id = ann_dict.get("container_id") or getattr(annotation, "container_id", None)
                file_id = ann_dict.get("file_id") or getattr(annotation, "file_id", None)
                filename = ann_dict.get("filename") or getattr(annotation, "filename", None)

                if container_id and file_id:
                    self._register_container_file(
                        filename=filename,
                        file_id=file_id,
                        container_id=container_id,
                    )
                    self._attachments.append(
                        {
                            "file_id": file_id,
                            "container_id": container_id,
                            "filename": filename,
                        }
                    )

    async def _attach_container_file_metadata(self, raw_message: Any) -> None:
        """
        Persist attachments to Supabase (marketing_messages.attachments & marketing_attachments).
        """
        try:
            thread_id = self._ctx.thread.id if self._ctx and self._ctx.thread else None
            item_id = getattr(raw_message, "id", None) or self._get_field(raw_message, "id")
            if not thread_id or not item_id:
                logger.debug("Cannot attach metadata: missing thread_id or item_id")
                return

            attachments = list(getattr(self, "_attachments", []) or [])
            if not attachments:
                logger.debug("No attachments collected; skip metadata attach")
                return

            from app.infrastructure.supabase.client import get_supabase

            sb = get_supabase()
            # Update marketing_messages.attachments
            try:
                sb.table("marketing_messages").update({"attachments": attachments}).eq("id", item_id).execute()
            except Exception:
                logger.exception("Failed to persist attachments on marketing_messages for %s", item_id)

            # Upsert marketing_attachments for searchability
            for att in attachments:
                try:
                    sb.table("marketing_attachments").upsert(
                        {
                            "id": att["file_id"],
                            "conversation_id": thread_id,
                            "owner_email": getattr(self._ctx.request_context, "user_email", None),
                            "filename": att.get("filename"),
                            "storage_metadata": {
                                "container_id": att.get("container_id"),
                            },
                        }
                    ).execute()
                except Exception:
                    logger.exception("Failed to upsert marketing_attachment %s", att.get("file_id"))

            logger.info("Saved %d attachments for message %s", len(attachments), item_id)
            # clear for next message
            self._attachments.clear()
        except Exception:
            logger.exception("Unexpected error while attaching container file metadata")

    async def _rewrite_assistant_message_links(self, raw_message: Any) -> None:
        """
        After container files are registered for a message, rewrite sandbox links in the
        stored AssistantMessageItem so that future renders use backend download URLs.
        """
        try:
            thread_id = self._ctx.thread.id if self._ctx and self._ctx.thread else None
            item_id = getattr(raw_message, "id", None) or self._get_field(raw_message, "id")
            if not thread_id or not item_id:
                logger.debug("Cannot rewrite links: missing thread_id or item_id")
                return

            container_files = dict(getattr(self, "_container_files", {}) or {})
            if not container_files:
                logger.debug("No container files registered; skip rewrite")
                return

            # Load the saved thread item
            try:
                item = await self._ctx.store.load_item(
                    thread_id,
                    item_id,
                    self._ctx.request_context,
                )
            except Exception:
                logger.exception(
                    "Failed to load thread item for link rewrite: thread=%s item=%s",
                    thread_id,
                    item_id,
                )
                return

            if not isinstance(item, AssistantMessageItem):
                logger.debug(
                    "Skip rewrite: item %s is not AssistantMessageItem (type=%s)",
                    item_id,
                    getattr(item, "type", None),
                )
                return

            changed = False
            for block in getattr(item, "content", []) or []:
                text = getattr(block, "text", None)
                if not text:
                    continue
                new_text = self._rewrite_text_with_container_files(text, container_files)
                if new_text != text:
                    block.text = new_text
                    changed = True

            if not changed:
                logger.debug("No sandbox links rewritten for item %s", item_id)
                return

            try:
                await self._ctx.store.save_item(
                    thread_id,
                    item,
                    self._ctx.request_context,
                )
                logger.info(
                    "Rewrote sandbox links for assistant message %s in thread %s",
                    item_id,
                    thread_id,
                )

                # Notify clients in the current stream so UI refreshes immediately
                try:
                    await self._ctx.stream(ThreadItemReplacedEvent(item=item))
                except Exception:
                    logger.exception(
                        "Failed to stream ThreadItemReplacedEvent after rewrite: thread=%s item=%s",
                        thread_id,
                        item_id,
                    )
            except Exception:
                logger.exception(
                    "Failed to save rewritten assistant message: thread=%s item=%s",
                    thread_id,
                    item_id,
                )
        except Exception:
            logger.exception("Unexpected error while rewriting assistant message links")

    def _rewrite_text_with_container_files(
        self,
        text: str,
        container_files: Dict[str, Tuple[str, str]],
    ) -> str:
        """Replace sandbox:/ links with plain text labels (no hyperlink) to avoid in-message download links."""
        if not text or not container_files:
            return text

        def replacer(match: re.Match) -> str:
            label = match.group(1)
            sandbox_url = match.group(2)  # e.g. sandbox:/mnt/data/foo.csv
            path = sandbox_url.replace("sandbox:", "", 1)
            basename = path.split("/")[-1]

            candidates = [
                sandbox_url,
                path,
                f"/mnt/data/{basename}",
                f"sandbox:/mnt/data/{basename}",
                basename,
            ]

            ref: Tuple[str, str] | None = None
            for key in candidates:
                ref = container_files.get(key)
                if ref:
                    break

            if not ref:
                logger.warning(
                    "No container file mapping for sandbox url %s (keys tried=%s)",
                    sandbox_url,
                    candidates,
                )
                return match.group(0)

            # Return just the label (no hyperlink). Buttons are rendered separately from attachments metadata.
            return label

        return SANDBOX_LINK_RE.sub(replacer, text)

    def get_container_file_map(self) -> Dict[str, Tuple[str, str]]:
        """Return a copy of the current container file mapping."""
        return dict(self._container_files)

    # --- URL / token helpers -------------------------------------------------

    def _get_token_service(self) -> MarketingTokenService:
        if self._token_service:
            return self._token_service
        settings = get_settings()
        self._token_service = MarketingTokenService(settings.marketing_chatkit_token_secret)
        return self._token_service

    def _build_download_url(self, file_id: str, container_id: str | None) -> str:
        """
        Build a signed, relative download URL for the frontend proxy.
        Token is short‑lived and bound to file/container to avoid leaking secrets via headers.
        """
        try:
            svc = self._get_token_service()
            now = int(datetime.now().timestamp())
            ttl = max(get_settings().marketing_chatkit_token_ttl, 60)
            safe_file_id = self._sanitize_id(file_id)
            safe_container_id = self._sanitize_id(container_id) if container_id else None
            payload = {
                "sub": getattr(self._ctx.request_context, "user_id", "unknown"),
                "email": getattr(self._ctx.request_context, "user_email", "unknown"),
                "name": getattr(self._ctx.request_context, "user_name", None),
                "iat": now,
                "exp": now + ttl,
                "file_id": safe_file_id,
            }
            if safe_container_id:
                payload["container_id"] = safe_container_id
            token = svc.sign(payload)
            query = f"token={token}"
            if safe_container_id:
                query += f"&container_id={safe_container_id}"
            # URL‑encode file_id in path to avoid hidden chars breaking the link
            from urllib.parse import quote

            encoded_file_id = quote(safe_file_id, safe="")
            return f"/api/marketing/files/{encoded_file_id}?{query}"
        except Exception:
            logger.exception("Failed to sign download URL; falling back to unsigned")
            if container_id:
                return f"/api/marketing/files/{file_id}?container_id={container_id}"
            return f"/api/marketing/files/{file_id}"

    def _describe_tool_call(self, raw_item: Any) -> Optional[dict[str, Any]]:
        identifier = self._extract_identifier(raw_item)
        if not identifier:
            logger.warning(f"No identifier found for tool call: {raw_item}")
            return None
        identifiers = {identifier}
        secondary = self._get_field(raw_item, "call_id") or self._get_field(raw_item, "callId")
        if secondary:
            identifiers.add(secondary)

        tool_type = self._get_field(raw_item, "type") or "tool"
        name = self._get_field(raw_item, "name")
        server = self._get_field(raw_item, "server_label") or self._get_field(raw_item, "server")
        args_preview = self._format_arguments(self._get_field(raw_item, "arguments"))

        # Check for MCP calls - multiple possible type names
        is_mcp = (
            tool_type == "mcp_call"
            or tool_type == "mcp"
            or tool_type == "ability_call"
            or tool_type == "mcp_ability_call"
            or "mcp" in tool_type.lower()
            or server is not None  # If server_label exists, it's likely an MCP call
        )

        if tool_type == "web_search_call":
            title = "Web検索"
            icon = "search"
            desc = "OpenAI Web Search を実行中"
        elif is_mcp:
            title = f"MCP: {name or 'tool'}"
            icon = "bolt"
            desc = f"サーバー: {server}" if server else "MCP ツール呼び出し"
        elif tool_type == "code_interpreter_call":
            title = "Code Interpreter"
            icon = "square-code"
            desc = "Code Interpreter を実行中"
        else:
            # Check if it's a function call
            if tool_type == "function_call" or tool_type == "function":
                title = f"Function: {name or 'tool'}"
                icon = "square-code"  # Use valid icon
                desc = "Function ツール呼び出し"
            else:
                title = name or "外部ツール"
                icon = "square-text"
                desc = f"ツール呼び出し (type: {tool_type})"

        if args_preview:
            desc = f"{desc}\n引数: {args_preview}"

        logger.info(f"Tool description: title={title}, type={tool_type}, is_mcp={is_mcp}")

        return {
            "identifiers": identifiers,
            "title": title,
            "icon": icon,
            "description": desc,
        }

    def _summarize_output(self, output: Any) -> str | None:
        if output is None:
            return "完了"
        if isinstance(output, str):
            text = output.strip()
        else:
            try:
                text = json.dumps(output, ensure_ascii=False)
            except TypeError:
                text = str(output)
        return text[:420] + ("…" if len(text) > 420 else "")

    def _format_arguments(self, arguments: Any) -> str | None:
        if not arguments:
            return None
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
            except json.JSONDecodeError:
                text = arguments.strip()
            else:
                if isinstance(parsed, dict):
                    text = ", ".join(
                        f"{k}={self._short(v)}" for k, v in parsed.items()
                    )
                else:
                    text = str(parsed)
        elif isinstance(arguments, dict):
            text = ", ".join(
                f"{k}={self._short(v)}" for k, v in arguments.items()
            )
        else:
            text = str(arguments)
        return text[:200]

    def _short(self, value: Any) -> str:
        text = str(value)
        return text if len(text) <= 24 else text[:21] + "…"

    def _extract_identifier(self, raw_item: Any) -> Optional[str]:
        # Try multiple possible identifier field names
        identifier = (
            self._get_field(raw_item, "call_id")
            or self._get_field(raw_item, "callId")
            or self._get_field(raw_item, "id")
            or self._get_field(raw_item, "tool_call_id")
            or self._get_field(raw_item, "ability_id")
        )
        if not identifier:
            logger.debug(f"Could not extract identifier from raw_item: {raw_item}")
        return identifier

    def _get_field(self, obj: Any, name: str) -> Optional[Any]:
        if hasattr(obj, name):
            return getattr(obj, name)
        if isinstance(obj, dict):
            return obj.get(name)
        return None


def instrument_run_result(result, tracker: ToolUsageTracker) -> InstrumentedRunResult:
    return InstrumentedRunResult(result, tracker.observe)
