from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional

from agents.stream_events import RunItemStreamEvent, StreamEvent
from chatkit.agents import AgentContext
from chatkit.types import (
    CustomTask,
    ThreadItemUpdated,
    WorkflowItem,
    WorkflowTaskAdded,
    WorkflowTaskUpdated,
)


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

    async def observe(self, event: StreamEvent) -> None:
        if not isinstance(event, RunItemStreamEvent):
            return
        if event.name == "tool_called":
            metadata = self._describe_tool_call(event.item.raw_item)
            if metadata:
                await self._presenter.add_tool(**metadata)
        elif event.name == "tool_output":
            identifier = self._extract_identifier(event.item.raw_item)
            if identifier:
                summary = self._summarize_output(event.item.output)
                await self._presenter.complete_tool(identifier, summary)

    async def close(self) -> None:
        await self._presenter.close()

    def _describe_tool_call(self, raw_item: Any) -> Optional[dict[str, Any]]:
        identifier = self._extract_identifier(raw_item)
        if not identifier:
            return None
        identifiers = {identifier}
        secondary = self._get_field(raw_item, "call_id") or self._get_field(raw_item, "callId")
        if secondary:
            identifiers.add(secondary)

        tool_type = self._get_field(raw_item, "type") or "tool"
        name = self._get_field(raw_item, "name")
        server = self._get_field(raw_item, "server_label")
        args_preview = self._format_arguments(self._get_field(raw_item, "arguments"))

        if tool_type == "web_search_call":
            title = "Web検索"
            icon = "search"
            desc = "OpenAI Web Search を実行中"
        elif tool_type == "mcp_call":
            title = f"MCP: {name or 'tool'}"
            icon = "bolt"
            desc = f"サーバー: {server}" if server else "MCP ツール呼び出し"
        elif tool_type == "code_interpreter_call":
            title = "Code Interpreter"
            icon = "square-code"
            desc = "Code Interpreter を実行中"
        else:
            title = name or "外部ツール"
            icon = "square-text"
            desc = "外部ツールを実行中"

        if args_preview:
            desc = f"{desc}\n引数: {args_preview}"

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
        return (
            self._get_field(raw_item, "call_id")
            or self._get_field(raw_item, "callId")
            or self._get_field(raw_item, "id")
        )

    def _get_field(self, obj: Any, name: str) -> Optional[Any]:
        if hasattr(obj, name):
            return getattr(obj, name)
        if isinstance(obj, dict):
            return obj.get(name)
        return None


def instrument_run_result(result, tracker: ToolUsageTracker) -> InstrumentedRunResult:
    return InstrumentedRunResult(result, tracker.observe)
