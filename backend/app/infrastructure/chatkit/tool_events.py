from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional

from agents.stream_events import RunItemStreamEvent, StreamEvent
from chatkit.agents import AgentContext
from chatkit.types import (
    CustomSummary,
    CustomTask,
    ThreadItemAddedEvent,
    ThreadItemDoneEvent,
    ThreadItemUpdated,
    Workflow,
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

    async def add_tool(self, *, identifiers: Iterable[str], title: str, icon: str, description: str | None) -> None:
        await self._ensure_workflow()
        if not self._workflow_item:
            return
        task = CustomTask(
            title=title,
            icon=icon,
            content=description,
            status_indicator="loading",
        )
        workflow = self._workflow_item.workflow
        workflow.tasks.append(task)
        index = len(workflow.tasks) - 1
        await self._ctx.stream(
            ThreadItemUpdated(
                item_id=self._workflow_item.id,
                update=WorkflowTaskAdded(task=task, task_index=index),
            )
        )
        ref = TaskRef(task=task, index=index, identifiers=set(identifiers))
        for ident in ref.identifiers:
            self._lookup[ident] = ref

    async def complete_tool(self, identifier: str, summary: str | None) -> None:
        if not self._workflow_item:
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
                item_id=self._workflow_item.id,
                update=WorkflowTaskUpdated(task=ref.task, task_index=ref.index),
            )
        )
        for key in list(ref.identifiers):
            self._lookup.pop(key, None)

    async def finalize(self) -> None:
        if not self._workflow_item:
            return
        workflow = self._workflow_item.workflow
        if workflow.summary is None:
            workflow.summary = CustomSummary(title="外部ツール実行ログ", icon="sparkle")
        workflow.expanded = False
        await self._ctx.stream(ThreadItemDoneEvent(item=self._workflow_item))
        await self._ctx.store.add_thread_item(
            self._workflow_item.thread_id,
            self._workflow_item,
            self._ctx.request_context,
        )
        self._workflow_item = None
        self._lookup.clear()

    async def _ensure_workflow(self) -> None:
        if self._workflow_item is not None:
            return
        workflow = Workflow(
            type="custom",
            tasks=[],
            summary=CustomSummary(title="外部ツール実行ログ", icon="sparkle"),
            expanded=True,
        )
        self._workflow_item = WorkflowItem(
            id=self._ctx.generate_id("workflow"),
            created_at=datetime.now(),
            workflow=workflow,
            thread_id=self._ctx.thread.id,
        )
        await self._ctx.stream(ThreadItemAddedEvent(item=self._workflow_item))


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
        self._ctx = ctx
        self._presenter = ToolWorkflowPresenter(ctx)

    async def observe(self, event: StreamEvent) -> None:
        if not isinstance(event, RunItemStreamEvent):
            return
        if event.name == "tool_called":
            metadata = self._describe_tool_call(event.item.raw_item)
            if not metadata:
                return
            await self._presenter.add_tool(**metadata)
        elif event.name == "tool_output":
            identifier = self._extract_identifier(event.item.raw_item)
            if not identifier:
                return
            summary = self._summarize_output(event.item.output)
            await self._presenter.complete_tool(identifier, summary)

    async def close(self) -> None:
        await self._presenter.finalize()

    def _describe_tool_call(self, raw_item: Any) -> dict[str, Any] | None:
        identifier = self._extract_identifier(raw_item)
        if not identifier:
            return None
        identifiers = {identifier}
        call_id = self._get_field(raw_item, "call_id") or self._get_field(raw_item, "callId")
        if call_id:
            identifiers.add(call_id)

        tool_type = self._get_field(raw_item, "type") or "tool"
        name = self._get_field(raw_item, "name")
        server = self._get_field(raw_item, "server_label")
        arguments = self._format_arguments_preview(self._get_field(raw_item, "arguments"))

        if tool_type == "web_search_call":
            title = "Web検索"
            icon = "search"
            description = "OpenAI Web Search を実行中"
        elif tool_type == "mcp_call":
            icon = "bolt"
            title = f"MCP: {name or 'tool'}"
            description = f"サーバー: {server}" if server else "MCP ツール呼び出し"
        elif tool_type == "code_interpreter_call":
            title = "Code Interpreter"
            icon = "square-code"
            description = "Python サンドボックスでコードを実行中"
        else:
            title = name or "外部ツール"
            icon = "square-text"
            description = "外部ツールを実行中"

        if arguments:
            description = f"{description}\n引数: {arguments}"

        return {
            "identifiers": identifiers,
            "title": title,
            "icon": icon,
            "description": description,
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

    def _format_arguments_preview(self, arguments: Any) -> str | None:
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
                        f"{key}={self._truncate_value(value)}" for key, value in parsed.items()
                    )
                else:
                    text = str(parsed)
        elif isinstance(arguments, dict):
            text = ", ".join(
                f"{key}={self._truncate_value(value)}" for key, value in arguments.items()
            )
        else:
            text = str(arguments)
        return text[:200]

    def _truncate_value(self, value: Any) -> str:
        text = str(value)
        return text[:24] + "…" if len(text) > 24 else text

    def _extract_identifier(self, raw_item: Any) -> str | None:
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
