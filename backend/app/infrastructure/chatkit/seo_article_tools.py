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
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from agents import RunContextWrapper, apply_diff, function_tool
from chatkit.agents import AgentContext, ClientToolCall
from openai import AsyncOpenAI
from app.infrastructure.supabase.client import get_supabase

DEFAULT_FILE_NAME = "article.html"
ALLOWED_FILE_NAMES = {DEFAULT_FILE_NAME, "article.md", "article_body.html"}
ALLOWED_STATUSES = {"draft", "in_progress", "published", "archived"}
STATUS_ALIASES = {
    "outline_created": "in_progress",
    "outline_ready": "in_progress",
    "ready_for_review": "in_progress",
    "ready": "in_progress",
}
MARKETING_ARTICLES_TABLE = "marketing_articles"
logger = logging.getLogger(__name__)


@dataclass
class ArticleState:
    article_id: str
    conversation_id: str = ""
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
        conversation_id=raw.get("conversation_id") or agent_ctx.thread.id,
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


def _sb():
    try:
        return get_supabase()
    except Exception:
        logger.exception("Failed to initialize Supabase client")
        raise


def _refresh_state_from_db(agent_ctx: AgentContext, state: ArticleState) -> ArticleState:
    """最新の記事を Supabase から取得し、見つかれば state を更新して返す。"""
    sb = _sb()
    article_id = state.article_id or agent_ctx.thread.id
    conversation_id = state.conversation_id or agent_ctx.thread.id

    res = (
        sb.table(MARKETING_ARTICLES_TABLE)
        .select("*")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []

    # article_id で見つからなければ conversation 単位の最新記事を拾う
    if not rows:
        res = (
            sb.table(MARKETING_ARTICLES_TABLE)
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []

    if not rows:
        state.conversation_id = conversation_id
        return state

    row = rows[0]
    state.article_id = row.get("id") or state.article_id
    state.conversation_id = row.get("conversation_id") or conversation_id
    state.title = row.get("title") or state.title
    state.outline = row.get("outline") or state.outline
    state.body = row.get("body_html") or state.body
    state.language = row.get("language") or state.language
    state.version = int(row.get("version") or state.version or 0)
    state.status = row.get("status") or state.status
    return state


def _upsert_article(agent_ctx: AgentContext, state: ArticleState) -> None:
    """Supabase に記事を永続化する。"""
    sb = _sb()
    conversation_id = state.conversation_id or agent_ctx.thread.id
    payload = {
        "id": state.article_id,
        "conversation_id": conversation_id,
        "title": state.title or None,
        "outline": state.outline or None,
        "body_html": state.body or "",
        "language": state.language or "ja",
        "version": state.version or 1,
        "status": state.status or "draft",
        "metadata": {},
    }
    sb.table(MARKETING_ARTICLES_TABLE).upsert(payload).execute()
    state.conversation_id = conversation_id


def _emit_client_tool(agent_ctx: AgentContext, name: str, arguments: Dict[str, Any]) -> None:
    agent_ctx.client_tool_call = ClientToolCall(name=name, arguments=arguments)


def _normalize_status(status: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Validate/normalize status. Returns (normalized_status, warning_or_none)."""
    if status is None:
        return None, None
    if status in ALLOWED_STATUSES:
        return status, None
    if status in STATUS_ALIASES:
        normalized = STATUS_ALIASES[status]
        return normalized, f"Status '{status}' is not allowed; coerced to '{normalized}'."
    return None, f"Invalid status '{status}'. Allowed: {sorted(ALLOWED_STATUSES)}"


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
    state = _refresh_state_from_db(agent_ctx, state)
    await _save_state(agent_ctx, state)
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
    return {"opened": True, "article_id": state.article_id, "mode": mode}


@function_tool(
    name_override="seo_update_canvas",
    description_override="Push the latest SEO article metadata to the canvas (bodyは内部状態のみ反映、引数では変更しない)。",
)
async def seo_update_canvas(
    ctx: RunContextWrapper[AgentContext],
    article_id: Optional[str] = None,
    title: Optional[str] = None,
    outline: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    agent_ctx = _require_agent_ctx(ctx)
    state = _load_state(agent_ctx)
    state.conversation_id = state.conversation_id or agent_ctx.thread.id
    state = _refresh_state_from_db(agent_ctx, state)

    changed = False
    if article_id and article_id != state.article_id:
        state.article_id = article_id
        changed = True
    if title is not None:
        state.title = title
        changed = True
    if outline is not None:
        state.outline = outline
        changed = True
    if status is not None:
        state.status = status
        changed = True

    if changed:
        state.version = (state.version or 0) + 1
        _upsert_article(agent_ctx, state)
    # body 引数は受け付けない（apply_patch でのみ変更）
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
        conversation_id=agent_ctx.thread.id,
        title=topic or "",
        outline="",
        body="",
        language=language,
        version=1,
        status="draft",
    )
    await _save_state(agent_ctx, state)  # 会話行を先に作成
    _upsert_article(agent_ctx, state)
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
    state = _refresh_state_from_db(agent_ctx, state)
    await _save_state(agent_ctx, state)
    return asdict(state)


@function_tool(name_override="save_seo_article", description_override="Persist the SEO article (title/outline/status) and push canvas update. Body は apply_patch 専用。")
async def save_seo_article(
    ctx: RunContextWrapper[AgentContext],
    article_id: Optional[str] = None,
    title: Optional[str] = None,
    outline: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    agent_ctx = _require_agent_ctx(ctx)
    state = _load_state(agent_ctx)
    state.conversation_id = state.conversation_id or agent_ctx.thread.id
    state = _refresh_state_from_db(agent_ctx, state)

    if article_id:
        state.article_id = article_id
    if title is not None:
        state.title = title
    if outline is not None:
        state.outline = outline
    if status is not None:
        normalized, warn = _normalize_status(status)
        if normalized is None:
            await _save_state(agent_ctx, state)
            return {
                "article_id": state.article_id,
                "version": state.version,
                "status": state.status,
                "notice": warn,
            }
        state.status = normalized

    state.version = (state.version or 0) + 1
    _upsert_article(agent_ctx, state)
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
        "status": state.status,
        **({"notice": warn} if status is not None and warn else {}),
    }


@function_tool(
    name_override="save_seo_article_body",
    description_override="Save full HTML body of the SEO article without apply_patch. 初稿や上書き専用。本文が既にある場合は overwrite=true で上書き、通常は apply_patch_to_article を使う。",
)
async def save_seo_article_body(
    ctx: RunContextWrapper[AgentContext],
    body: str,
    article_id: Optional[str] = None,
    status: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """初回の本文保存や全文差し替えを apply_patch なしで実行する。

    overwrite=False かつ既存本文がある場合は何もしないで notice を返す。
    """
    agent_ctx = _require_agent_ctx(ctx)
    state = _load_state(agent_ctx)
    state.conversation_id = state.conversation_id or agent_ctx.thread.id
    if article_id:
        state.article_id = article_id
    state = _refresh_state_from_db(agent_ctx, state)

    if state.body and not overwrite:
        await _save_state(agent_ctx, state)
        return {
            "article_id": state.article_id,
            "version": state.version,
            "status": state.status,
            "notice": "Body already exists; use apply_patch_to_article or set overwrite=true.",
        }

    state.body = body
    warn_status: Optional[str] = None
    if status is not None:
        normalized, warn = _normalize_status(status)
        if normalized is None:
            await _save_state(agent_ctx, state)
            return {
                "article_id": state.article_id,
                "version": state.version,
                "status": state.status,
                "notice": warn,
            }
        state.status = normalized
        warn_status = warn
    state.version = (state.version or 0) + 1
    _upsert_article(agent_ctx, state)
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
        "status": state.status,
        **({"notice": warn_status} if warn_status else {}),
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
    state.conversation_id = state.conversation_id or agent_ctx.thread.id
    state = _refresh_state_from_db(agent_ctx, state)

    try:
        patched_body, applied = await _run_apply_patch(state.body, user_instruction)
    except Exception as exc:  # noqa: BLE001
        # 失敗時は状態を一切変えずに通知だけ返す
        return {
            "article_id": state.article_id,
            "version": state.version,
            "body": state.body,
            "notice": f"apply_patch failed: {exc}",
        }

    if not applied:
        await _save_state(agent_ctx, state)
        return {
            "article_id": state.article_id,
            "version": state.version,
            "body": state.body,
            "notice": "No apply_patch operations applied (tool call missing or failed); article unchanged",
        }

    if patched_body.strip() == state.body.strip():
        await _save_state(agent_ctx, state)
        return {
            "article_id": state.article_id,
            "version": state.version,
            "body": state.body,
            "notice": "No changes applied",
        }

    state.body = patched_body
    state.version = (state.version or 0) + 1
    _upsert_article(agent_ctx, state)
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


async def _run_apply_patch(current_body: str, user_instruction: str) -> tuple[str, bool]:
    """apply_patch を公式フローで実行し、差分を apply_diff で適用して返す。

    1) responses.create で apply_patch_call を受け取る
    2) operation.diff を apply_diff で適用（記事本文はメモリ上で管理）
    3) それぞれの結果を apply_patch_call_output として返し、モデルに再応答させる
    4) apply_patch_call がなくなるか 3 ラウンド繰り返したら終了
    成功時: (適用後本文, True) を返す
    apply_patch_call が一度も無い/適用できない場合: (元本文, False) を返す
    失敗時は例外を投げる
    """

    client = AsyncOpenAI()
    body = current_body
    applied = False
    pending_input: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are an editor for a Japanese SEO article written in HTML. Use the "
                f"apply_patch tool and emit update_file operations for {DEFAULT_FILE_NAME} only. Prefer "
                "V4A diffs in operation.diff, but if you cannot produce a diff you may provide "
                "operation.new_content as the full updated file. Keep existing sections unless 指示 で削除する場合のみ。"
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Edit the article (HTML). Respond by calling apply_patch with update_file "
                        f"for {DEFAULT_FILE_NAME}. Provide the changes as a V4A diff in operation.diff; do "
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

        # apply_patch_call が無ければ終了（本文は変更しない）
        if not apply_calls:
            break

        # diff を適用して結果を model に返す
        call_outputs = []
        for call in apply_calls:
            op = _maybe_dump(call.get("operation"))
            call_id = call.get("call_id") or call.get("id")
            status = "failed"
            message = ""

            path = op.get("path") or DEFAULT_FILE_NAME
            if path not in ALLOWED_FILE_NAMES:
                message = f"Unexpected path {path}; expected one of {sorted(ALLOWED_FILE_NAMES)}"
            else:
                diff = op.get("diff") or op.get("patch")
                new_content = op.get("new_content")
                if diff:
                    try:
                        body = apply_diff(body, diff, create=(op.get("type") == "create_file"))
                        status = "completed"
                        message = f"patched {path}"
                        applied = True
                    except Exception as exc:  # noqa: BLE001
                        message = f"apply_diff error: {exc}"
                elif new_content:
                    # モデルが new_content を返した場合はそのまま置き換え
                    body = new_content
                    status = "completed"
                    message = f"replaced {path} with new_content"
                    applied = True
                else:
                    message = "Missing diff or new_content for update_file"

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

    return body, applied


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
