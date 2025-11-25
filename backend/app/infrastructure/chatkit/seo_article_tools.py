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

from agents import RunContextWrapper, apply_diff, function_tool
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

    The model is guided to emit a single update_file operation containing a V4A `diff` for
    article.md (HTML). If parsing/apply fails, the original body is returned to avoid data loss.
    """

    client = AsyncOpenAI()
    response = await client.responses.create(
        model="gpt-5.1",
        tools=[{"type": "apply_patch"}],
        input=[
            {
                "role": "system",
                "content": (
                "You are an editor for a Japanese SEO article written in HTML. Use the "
                "apply_patch tool and emit exactly one update_file operation for article.md, "
                "supplying a V4A diff in operation.diff (no new_content). Keep existing sections "
                "unless指示で削除される場合のみ消す。差分は最小限かつ有効なパッチにすること。"
            ),
        },
        {
            "role": "user",
            "content": [
                    {
                        # Responses API (v2024-12) requires `input_text` instead of the legacy `text`.
                        "type": "input_text",
                        "text": (
                            "Edit the article (HTML). Respond by calling apply_patch with a single "
                            "update_file operation for article.md. Provide the changes as a V4A "
                            "diff in operation.diff; do NOT include new_content.\n\n"
                            f"Current article (path {DEFAULT_FILE_NAME}):\n" + current_body
                            + "\n\nEdit request:\n" + user_instruction
                        ),
                    }
                ],
            },
        ],
    )

    return _extract_patched_body(response, current_body)


def _extract_patched_body(response: Any, fallback: str) -> str:
    output_items = _to_list(
        getattr(response, "output", None)
        or getattr(response, "data", None)
        or _maybe_dump(response).get("output")
    )
    if not output_items:
        return fallback

    for item in output_items:
        item_dict = _maybe_dump(item)
        item_type = item_dict.get("type")

        # Newer Responses output: apply_patch_call items
        if item_type == "apply_patch_call":
            op = item_dict.get("operation") or {}
            patched = _patched_from_apply_patch_call(op, fallback)
            if patched:
                return patched

        # Legacy tool_call output
        if item_type == "tool_call":
            tool_call = item_dict.get("tool_call") or {}
            if (tool_call.get("type") or tool_call.get("tool", {}).get("type")) != "apply_patch":
                continue
            arguments = tool_call.get("arguments") or {}
            patched = _patched_from_operations(arguments, fallback)
            if patched:
                return patched

        # Textual fallbacks
        content = item_dict.get("content")
        if content:
            texts: list[str] = []
            if isinstance(content, list):
                for seg in content:
                    seg_dict = _maybe_dump(seg)
                    text = seg_dict.get("text")
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
    args_dict = _maybe_dump(arguments)
    operations = _to_list(
        args_dict.get("operations")
        or args_dict.get("patches")
        or []
    )

    target_names = {
        args_dict.get("file"),
        args_dict.get("path"),
        args_dict.get("file_path"),
        DEFAULT_FILE_NAME,
    }

    for op in operations:
        op_dict = _maybe_dump(op)
        op_type = op_dict.get("type") or op_dict.get("operation") or op_dict.get("op")
        path = op_dict.get("path") or op_dict.get("file") or op_dict.get("file_path") or DEFAULT_FILE_NAME
        if op_type in {"update_file", "create_file", "replace"} and (path in target_names):
            new_content = op_dict.get("new_content") or op_dict.get("content") or op_dict.get("text")
            if new_content:
                return new_content

    return None


def _patched_from_apply_patch_call(operation: Dict[str, Any], fallback: str) -> Optional[str]:
    if not operation:
        return None

    op_dict = _maybe_dump(operation)
    op_type = op_dict.get("type")
    path = op_dict.get("path") or DEFAULT_FILE_NAME
    target_ok = (path == DEFAULT_FILE_NAME) or (path is None)

    # Preferred: apply diff (V4A) provided by apply_patch tool
    diff = op_dict.get("diff") or op_dict.get("patch")
    if diff and target_ok:
        try:
            return apply_diff(fallback, diff, create=(op_type == "create_file"))
        except Exception:
            return None

    # Fallback: accept new_content/content if present
    new_content = op_dict.get("new_content") or op_dict.get("content")
    if new_content and target_ok:
        return new_content

    return None


def _maybe_dump(obj: Any) -> Dict[str, Any]:
    """Coerce pydantic/BaseModel/typed objects or dicts into plain dicts."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(exclude_none=True)
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return {}


def _to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
