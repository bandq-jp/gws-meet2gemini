"""SEO記事用のカスタムツール群 (ChatKit クライアントツール + apply_patch 編集).

これらのツールはマーケティング専用エージェントから呼ばれ、以下を担う:
- 記事ステートの永続化 (スレッド metadata に格納)
- ChatKit の Client Tool 経由で Canvas を開閉・更新
- GPT-5.1 apply_patch を使った差分編集

注意: ChatKit 側で Client Tool を扱うため、AgentContext を RunContextWrapper 経由で
context として渡す必要がある。marketing_server.py で Runner.run_streamed に context を
渡すようにしておくこと。
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from agents import RunContextWrapper, function_tool
from chatkit.agents import AgentContext, ClientToolCall
from openai import AsyncOpenAI

DEFAULT_FILE_NAME = "article.md"


@dataclass
class ArticleState:
    article_id: str
    title: str = ""
    outline: str = ""
    body: str = ""
    language: str = "ja"
    version: int = 0
    status: str = "draft"


def _require_agent_ctx(ctx: RunContextWrapper[AgentContext]) -> AgentContext:
    agent_ctx = ctx.context
    if agent_ctx is None:
        raise ValueError("AgentContext is missing; pass context into Runner.run_streamed().")
    return agent_ctx


def _load_state(agent_ctx: AgentContext) -> ArticleState:
    meta: Dict[str, Any] = agent_ctx.thread.metadata or {}
    raw = meta.get("seo_article") or {}
    return ArticleState(
        article_id=raw.get("article_id") or agent_ctx.thread.id,
        title=raw.get("title") or "",
        outline=raw.get("outline") or "",
        body=raw.get("body") or "",
        language=raw.get("language") or "ja",
        version=int(raw.get("version") or 0),
        status=raw.get("status") or "draft",
    )


async def _save_state(agent_ctx: AgentContext, state: ArticleState) -> None:
    meta: Dict[str, Any] = dict(agent_ctx.thread.metadata or {})
    meta["seo_article"] = asdict(state)
    agent_ctx.thread.metadata = meta
    await agent_ctx.store.save_thread(agent_ctx.thread, agent_ctx.request_context)


def _emit_client_tool(agent_ctx: AgentContext, name: str, arguments: Dict[str, Any]) -> None:
    agent_ctx.client_tool_call = ClientToolCall(name=name, arguments=arguments)


@function_tool(name_override="seo_open_canvas", description_override="Open the SEO article canvas on the client UI.")
async def seo_open_canvas(
    ctx: RunContextWrapper[AgentContext],
    article_id: Optional[str] = None,
    mode: str = "create",
    topic: Optional[str] = None,
    primary_keyword: Optional[str] = None,
) -> Dict[str, Any]:
    agent_ctx = _require_agent_ctx(ctx)
    state = _load_state(agent_ctx)
    if article_id:
        state.article_id = article_id
    _emit_client_tool(
        agent_ctx,
        "seo_open_canvas",
        {
            "articleId": state.article_id,
            "mode": mode,
            "topic": topic,
            "primaryKeyword": primary_keyword,
        },
    )
    await _save_state(agent_ctx, state)
    return {"opened": True, "article_id": state.article_id, "mode": mode}


@function_tool(name_override="seo_update_canvas", description_override="Push the latest SEO article content to the canvas.")
async def seo_update_canvas(
    ctx: RunContextWrapper[AgentContext],
    article_id: Optional[str] = None,
    title: Optional[str] = None,
    outline: Optional[str] = None,
    body: Optional[str] = None,
    version: Optional[int] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    agent_ctx = _require_agent_ctx(ctx)
    state = _load_state(agent_ctx)
    if article_id:
        state.article_id = article_id
    if title is not None:
        state.title = title
    if outline is not None:
        state.outline = outline
    if body is not None:
        state.body = body
    if status is not None:
        state.status = status
    if version is not None:
        state.version = version
    _emit_client_tool(
        agent_ctx,
        "seo_update_canvas",
        {
            "articleId": state.article_id,
            "title": state.title,
            "outline": state.outline,
            "body": state.body,
            "version": state.version,
            "status": state.status,
        },
    )
    await _save_state(agent_ctx, state)
    return {"ok": True, "article_id": state.article_id, "version": state.version}


@function_tool(name_override="create_seo_article", description_override="Start a new SEO article and open the canvas.")
async def create_seo_article(
    ctx: RunContextWrapper[AgentContext],
    topic: Optional[str] = None,
    primary_keyword: Optional[str] = None,
    language: str = "ja",
) -> Dict[str, Any]:
    agent_ctx = _require_agent_ctx(ctx)
    state = ArticleState(
        article_id=str(uuid.uuid4()),
        title=topic or "",
        outline="",
        body="",
        language=language,
        version=1,
        status="draft",
    )
    await _save_state(agent_ctx, state)
    _emit_client_tool(
        agent_ctx,
        "seo_open_canvas",
        {
            "articleId": state.article_id,
            "mode": "create",
            "topic": topic,
            "primaryKeyword": primary_keyword,
        },
    )
    return {"article_id": state.article_id, "version": state.version, "language": state.language}


@function_tool(name_override="get_seo_article", description_override="Get the latest SEO article state for this thread.")
async def get_seo_article(ctx: RunContextWrapper[AgentContext]) -> Dict[str, Any]:
    agent_ctx = _require_agent_ctx(ctx)
    state = _load_state(agent_ctx)
    return asdict(state)


@function_tool(name_override="save_seo_article", description_override="Persist the SEO article (title/outline/body) and push canvas update.")
async def save_seo_article(
    ctx: RunContextWrapper[AgentContext],
    article_id: Optional[str] = None,
    title: Optional[str] = None,
    outline: Optional[str] = None,
    body: Optional[str] = None,
    status: Optional[str] = None,
    ) -> Dict[str, Any]:
    agent_ctx = _require_agent_ctx(ctx)
    state = _load_state(agent_ctx)
    if article_id:
        state.article_id = article_id
    if title is not None:
        state.title = title
    if outline is not None:
        state.outline = outline
    if body is not None:
        state.body = body
    if status is not None:
        state.status = status
    state.version += 1
    _emit_client_tool(
        agent_ctx,
        "seo_update_canvas",
        {
            "articleId": state.article_id,
            "title": state.title,
            "outline": state.outline,
            "body": state.body,
            "version": state.version,
            "status": state.status,
        },
    )
    await _save_state(agent_ctx, state)
    return {
        "article_id": state.article_id,
        "version": state.version,
        "status": state.status,
    }


@function_tool(name_override="apply_patch_to_article", description_override="Use GPT-5.1 apply_patch to edit the article body by diff.")
async def apply_patch_to_article(
    ctx: RunContextWrapper[AgentContext],
    user_instruction: str,
    article_id: Optional[str] = None,
) -> Dict[str, Any]:
    agent_ctx = _require_agent_ctx(ctx)
    state = _load_state(agent_ctx)
    if article_id:
        state.article_id = article_id

    patched_body = await _run_apply_patch(state.body, user_instruction)
    if patched_body.strip() == state.body.strip():
        return {
            "article_id": state.article_id,
            "version": state.version,
            "body": state.body,
            "notice": "No changes applied",
        }

    state.body = patched_body
    state.version += 1
    await _save_state(agent_ctx, state)
    _emit_client_tool(
        agent_ctx,
        "seo_update_canvas",
        {
            "articleId": state.article_id,
            "title": state.title,
            "outline": state.outline,
            "body": state.body,
            "version": state.version,
            "status": state.status,
        },
    )
    return {
        "article_id": state.article_id,
        "version": state.version,
        "body": state.body,
    }


async def _run_apply_patch(current_body: str, user_instruction: str) -> str:
    """Call Responses API with the built-in apply_patch tool and return patched body.

    The model is guided to emit an update_file operation with `new_content` so that parsing
    is straightforward. If parsing fails, the original body is returned to avoid data loss.
    """

    client = AsyncOpenAI()
    response = await client.responses.create(
        model="gpt-5.1",
        tools=[{"type": "apply_patch"}],
        input=[
            {
                "role": "system",
                "content": (
                    "You are an editor for a Japanese SEO article. Use the apply_patch tool and "
                    "emit an update_file operation whose new_content is the full, updated markdown "
                    "for the article. Do not drop existing sections unless explicitly requested."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Edit the article in markdown. Respond by calling apply_patch with an "
                            "update_file operation containing new_content.\n\n"
                            f"Current article (in {DEFAULT_FILE_NAME}):\n" + current_body
                            + "\n\nEdit request:\n" + user_instruction
                        ),
                    }
                ],
            },
        ],
    )

    return _extract_patched_body(response, current_body)


def _extract_patched_body(response: Any, fallback: str) -> str:
    output_items = getattr(response, "output", None) or getattr(response, "data", None)
    if not output_items and hasattr(response, "model_dump"):
        dumped = response.model_dump(exclude_none=True)
        output_items = dumped.get("output")

    if not output_items:
        return fallback

    for item in output_items:
        item_type = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
        if item_type == "tool_call":
            tool_call = getattr(item, "tool_call", None) or (item.get("tool_call") if isinstance(item, dict) else None)
            if not tool_call:
                continue
            tool_type = getattr(tool_call, "type", None) or (tool_call.get("type") if isinstance(tool_call, dict) else None)
            if tool_type != "apply_patch":
                continue
            arguments = getattr(tool_call, "arguments", None) or (tool_call.get("arguments") if isinstance(tool_call, dict) else None) or {}
            patched = _patched_from_operations(arguments, fallback)
            if patched:
                return patched

        content = getattr(item, "content", None) or (item.get("content") if isinstance(item, dict) else None)
        if content:
            texts: list[str] = []
            if isinstance(content, list):
                for seg in content:
                    text = getattr(seg, "text", None) or (seg.get("text") if isinstance(seg, dict) else None)
                    if text:
                        texts.append(text)
            elif isinstance(content, str):
                texts.append(content)
            if texts:
                joined = "\n".join(texts).strip()
                if joined:
                    return joined

    return fallback


def _patched_from_operations(arguments: Dict[str, Any], fallback: str) -> Optional[str]:
    operations = (
        arguments.get("operations")
        or arguments.get("patches")
        or []
    )

    target_names = {
        arguments.get("file"),
        arguments.get("path"),
        arguments.get("file_path"),
        DEFAULT_FILE_NAME,
    }

    for op in operations:
        if not isinstance(op, dict):
            continue
        op_type = op.get("type") or op.get("operation") or op.get("op")
        path = op.get("path") or op.get("file") or op.get("file_path") or DEFAULT_FILE_NAME
        if op_type in {"update_file", "create_file", "replace"} and (path in target_names):
            new_content = op.get("new_content") or op.get("content") or op.get("text")
            if new_content:
                return new_content

    return None
