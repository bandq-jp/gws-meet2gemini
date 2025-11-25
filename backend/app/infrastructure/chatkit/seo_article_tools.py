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
    """apply_patch を公式フローで実行し、差分を apply_diff で適用して返す。

    1) responses.create で apply_patch_call を受け取る
    2) operation.diff を apply_diff で適用（記事本文はメモリ上で管理）
    3) それぞれの結果を apply_patch_call_output として返し、モデルに再応答させる
    4) apply_patch_call がなくなるか 3 ラウンド繰り返したら終了
    失敗時は原文を返し、モデルには失敗メッセージを渡す。
    """

    client = AsyncOpenAI()
    body = current_body
    pending_input: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are an editor for a Japanese SEO article written in HTML. Use the "
                "apply_patch tool and emit update_file operations for article.md only. Provide "
                "V4A diffs in operation.diff (no new_content). Keep existing sections unless 指示 で削除する場合のみ。"
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Edit the article (HTML). Respond by calling apply_patch with update_file "
                        "for article.md. Provide the changes as a V4A diff in operation.diff; do "
                        "NOT include new_content.\n\n"
                        f"Current article (path {DEFAULT_FILE_NAME}):\n" + current_body
                        + "\n\nEdit request:\n" + user_instruction
                    ),
                }
            ],
        },
    ]

    prev_response_id: Optional[str] = None

    for _ in range(3):  # 防御的に最大3ラウンド
        resp = await client.responses.create(
            model="gpt-5.1",
            tools=[{"type": "apply_patch"}],
            input=pending_input,
            previous_response_id=prev_response_id,
        )

        output_items = _to_list(
            getattr(resp, "output", None)
            or getattr(resp, "data", None)
            or _maybe_dump(resp).get("output")
        )

        apply_calls = [
            _maybe_dump(item) for item in output_items if _maybe_dump(item).get("type") == "apply_patch_call"
        ]

        # apply_patch_call が無ければテキスト回答を拾って終了
        if not apply_calls:
            maybe_text = _extract_text_content(output_items)
            if maybe_text:
                body = maybe_text
            break

        # diff を適用して結果を model に返す
        call_outputs = []
        for call in apply_calls:
            op = _maybe_dump(call.get("operation"))
            call_id = call.get("call_id") or call.get("id")
            status = "failed"
            message = ""

            path = op.get("path") or DEFAULT_FILE_NAME
            if path != DEFAULT_FILE_NAME:
                message = f"Unexpected path {path}; expected {DEFAULT_FILE_NAME}"
            else:
                diff = op.get("diff") or op.get("patch")
                if not diff:
                    message = "Missing diff for update_file"
                else:
                    try:
                        body = apply_diff(body, diff, create=(op.get("type") == "create_file"))
                        status = "completed"
                        message = "patched article.md"
                    except Exception as exc:  # noqa: BLE001
                        message = f"apply_diff error: {exc}"

            call_outputs.append(
                {
                    "type": "apply_patch_call_output",
                    "call_id": call_id,
                    "status": status,
                    "output": message,
                }
            )

        # 次ラウンドの入力を apply_patch_call_output に差し替え
        pending_input = call_outputs
        prev_response_id = resp.id

    return body


def _extract_text_content(output_items: list[Any]) -> Optional[str]:
    """apply_patch_call が無い場合のテキスト回答抽出用"""

    texts: list[str] = []
    for item in output_items:
        item_dict = _maybe_dump(item)
        content = item_dict.get("content")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for seg in content:
                seg_dict = _maybe_dump(seg)
                text = seg_dict.get("text")
                if text:
                    texts.append(text)
    joined = "\n".join(t.strip() for t in texts if t)
    return joined or None


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
