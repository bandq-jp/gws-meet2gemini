from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional

from agents.stream_events import RunItemStreamEvent, StreamEvent
from chatkit.agents import AgentContext
from chatkit.types import (
    CustomTask,
    HiddenContextItem,
    ThreadItemUpdated,
    WorkflowItem,
    WorkflowTaskAdded,
    WorkflowTaskUpdated,
)

logger = logging.getLogger(__name__)


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

    async def observe(self, event: StreamEvent) -> None:
        if not isinstance(event, RunItemStreamEvent):
            return
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

            if identifier:
                summary = self._summarize_output(event.item.output)
                await self._presenter.complete_tool(identifier, summary)

                # Save tool output as hidden context for conversation history
                await self._save_tool_output_as_context(identifier, event.item)

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
