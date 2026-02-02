"""Marketing chat SSE streaming router.

Replaces the ChatKit-based /chatkit endpoint with direct SSE streaming
using MarketingAgentService + activity_items pattern.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.infrastructure.chatkit.agent_service import get_marketing_agent_service
from app.infrastructure.chatkit.ask_user_store import ask_user_store
from app.infrastructure.chatkit.context import MarketingRequestContext
from app.infrastructure.chatkit.keepalive import with_keepalive
from app.infrastructure.config.settings import get_settings
from app.infrastructure.security.marketing_token_service import (
    MarketingTokenError,
    MarketingTokenService,
)
from app.infrastructure.supabase.client import get_supabase

router = APIRouter(prefix="/marketing/chat", tags=["marketing-chat"])
logger = logging.getLogger(__name__)

# Title generation model
TITLE_MODEL = "gpt-4.1-mini"


def _gen_thread_id() -> str:
    return f"thr_{uuid.uuid4().hex[:12]}"


def _gen_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:12]}"


# ---------- Auth ----------

def _token_service() -> MarketingTokenService:
    settings = get_settings()
    return MarketingTokenService(settings.marketing_chatkit_token_secret)


async def require_marketing_context(
    authorization: Annotated[str | None, Header(convert_underscores=False)] = None,
    marketing_client_secret: Annotated[
        str | None, Header(alias="x-marketing-client-secret", convert_underscores=False)
    ] = None,
    model_asset_id: Annotated[
        str | None, Header(alias="x-model-asset-id", convert_underscores=False)
    ] = None,
) -> MarketingRequestContext:
    token: str | None = None
    if marketing_client_secret:
        token = marketing_client_secret.strip()
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing marketing client token",
        )
    try:
        claims = _token_service().verify(token)
    except MarketingTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    return MarketingRequestContext(
        user_id=claims.sub,
        user_email=claims.email,
        user_name=claims.name,
        model_asset_id=model_asset_id,
    )


# ---------- Schemas ----------

class ChatStreamRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    model_asset_id: str = "standard"
    attachment_file_ids: list[str] | None = None


class RespondRequest(BaseModel):
    group_id: str
    responses: dict[str, str]


class RenameRequest(BaseModel):
    title: str


# ---------- SSE Stream ----------

@router.post("/stream")
async def stream_marketing_chat(
    request: Request,
    body: ChatStreamRequest,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    supabase = get_supabase()
    agent_service = get_marketing_agent_service()

    # Get or create conversation
    conversation_id = body.conversation_id
    if not conversation_id:
        conversation_id = _gen_thread_id()
        supabase.table("marketing_conversations").insert({
            "id": conversation_id,
            "owner_clerk_id": context.user_id,
            "title": body.message[:50],
            "metadata": {"model_asset_id": body.model_asset_id},
        }).execute()

    # Save user message (content is JSONB column — store as JSON text object)
    supabase.table("marketing_messages").insert({
        "id": _gen_message_id(),
        "conversation_id": conversation_id,
        "role": "user",
        "content": {"type": "text", "text": body.message},
        "message_type": "user",
    }).execute()

    # Load context: prefer context_items, fallback to plain history
    conv_data = (
        supabase.table("marketing_conversations")
        .select("context_items")
        .eq("id", conversation_id)
        .single()
        .execute()
    )
    saved_context_items = conv_data.data.get("context_items") if conv_data.data else None

    conversation_history = None
    if not saved_context_items:
        msg_result = (
            supabase.table("marketing_messages")
            .select("role, content, message_type")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
        )
        conversation_history = []
        for m in msg_result.data:
            role = m["role"]
            if role not in ("user", "assistant"):
                continue
            content = m.get("content", "")
            # Extract text from JSONB content (dict from Supabase) or string
            if isinstance(content, dict):
                content = content.get("text", str(content))
            elif isinstance(content, list):
                texts = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                content = "\n".join(texts)
            elif isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "text" in parsed:
                        content = parsed["text"]
                except (json.JSONDecodeError, TypeError):
                    pass
            conversation_history.append({"role": role, "content": content})
        # Remove last user message since agent_service adds it
        if conversation_history and conversation_history[-1]["role"] == "user":
            conversation_history = conversation_history[:-1]

    async def event_generator():
        full_response = ""
        tool_calls_data: list[dict] = []
        activity_items: list[dict] = []
        current_text = ""
        seq = 0

        def _flush_text():
            nonlocal current_text, seq
            if current_text:
                seq += 1
                activity_items.append({
                    "kind": "text",
                    "sequence": seq,
                    "content": current_text,
                })
                current_text = ""

        try:
            raw_stream = agent_service.stream_chat(
                user_email=context.user_email,
                message=body.message,
                model_asset_id=body.model_asset_id,
                context_items=saved_context_items,
                conversation_history=conversation_history,
                attachment_file_ids=body.attachment_file_ids,
                conversation_id=conversation_id,
            )
            async for event in with_keepalive(raw_stream, interval=20):
                if await request.is_disconnected():
                    break

                # Handle reasoning translation
                if event.get("_needs_translation") and event.get("content"):
                    translated = await agent_service.translate_to_japanese(
                        event["content"]
                    )
                    event["content"] = translated
                event.pop("_needs_translation", None)

                # Intercept internal _context_items — save to DB, don't send
                if event["type"] == "_context_items":
                    try:
                        supabase.table("marketing_conversations").update(
                            {"context_items": event["items"]}
                        ).eq("id", conversation_id).execute()
                    except Exception as e:
                        logger.warning(f"Failed to save context_items: {e}")
                    continue

                # Intercept internal _ask_user_responses — persist into activity_items
                if event["type"] == "_ask_user_responses":
                    gid = event.get("group_id")
                    responses = event.get("responses")
                    if gid and responses:
                        for item in activity_items:
                            if item.get("kind") == "ask_user" and item.get("groupId") == gid:
                                item["responses"] = responses
                                break
                    continue  # Don't send to client

                # --- Collect activity items ---
                if event["type"] == "text_delta":
                    full_response += event.get("content", "")
                    current_text += event.get("content", "")
                elif event["type"] == "response_created":
                    _flush_text()
                elif event["type"] == "tool_call":
                    _flush_text()
                    tool_calls_data.append(event)
                    seq += 1
                    activity_items.append({
                        "kind": "tool",
                        "sequence": seq,
                        "name": event.get("name", "unknown"),
                        "call_id": event.get("call_id"),
                        "arguments": event.get("arguments"),
                    })
                elif event["type"] == "tool_result":
                    call_id = event.get("call_id")
                    for item in reversed(activity_items):
                        if (
                            item["kind"] == "tool"
                            and item.get("call_id") == call_id
                            and "output" not in item
                        ):
                            item["output"] = event.get("output", "(completed)")
                            break
                elif event["type"] == "reasoning":
                    _flush_text()
                    seq += 1
                    activity_items.append({
                        "kind": "reasoning",
                        "sequence": seq,
                        "content": event.get("content", ""),
                    })
                elif event["type"] == "ask_user":
                    _flush_text()
                    seq += 1
                    activity_items.append({
                        "kind": "ask_user",
                        "sequence": seq,
                        "groupId": event.get("group_id"),
                        "questions": event.get("questions"),
                    })
                elif event["type"] == "done":
                    _flush_text()

                    # Mark any unfinished tools as completed
                    for item in activity_items:
                        if item["kind"] == "tool" and "output" not in item:
                            item["output"] = "(completed)"

                    # Save assistant message with activity items
                    if full_response or activity_items:
                        msg_data = {
                            "id": _gen_message_id(),
                            "conversation_id": conversation_id,
                            "role": "assistant",
                            "content": {"type": "text", "text": full_response or ""},
                            "message_type": "assistant",
                        }
                        if activity_items:
                            msg_data["activity_items"] = activity_items
                        try:
                            supabase.table("marketing_messages").insert(
                                msg_data
                            ).execute()
                        except Exception:
                            # Fallback: activity_items column may not exist yet
                            msg_data.pop("activity_items", None)
                            supabase.table("marketing_messages").insert(
                                msg_data
                            ).execute()

                    # Update conversation timestamp
                    supabase.table("marketing_conversations").update(
                        {"updated_at": "now()"}
                    ).eq("id", conversation_id).execute()

                    event["conversation_id"] = conversation_id

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception("SSE event generator error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------- ask_user respond ----------

@router.post("/respond")
async def respond_to_question(
    body: RespondRequest,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    ok = ask_user_store.submit_responses(body.group_id, body.responses)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Question group not found or already answered",
        )
    return {"status": "ok"}


# ---------- Thread CRUD ----------

@router.get("/threads")
async def list_threads(
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    supabase = get_supabase()
    result = (
        supabase.table("marketing_conversations")
        .select("id, title, created_at, updated_at, metadata, is_shared")
        .eq("owner_clerk_id", context.user_id)
        .order("updated_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"threads": result.data}


@router.post("/threads")
async def create_thread(
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    supabase = get_supabase()
    thread_id = _gen_thread_id()
    result = (
        supabase.table("marketing_conversations")
        .insert({
            "id": thread_id,
            "owner_clerk_id": context.user_id,
            "title": "新しい会話",
        })
        .execute()
    )
    return result.data[0]


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    supabase = get_supabase()

    # Get conversation
    conv = (
        supabase.table("marketing_conversations")
        .select("id, title, owner_clerk_id, created_at, updated_at, metadata, is_shared")
        .eq("id", thread_id)
        .single()
        .execute()
    )
    if not conv.data:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Check permission
    is_owner = conv.data["owner_clerk_id"] == context.user_id
    is_shared = conv.data.get("is_shared", False)
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get messages
    msgs = (
        supabase.table("marketing_messages")
        .select("id, role, content, message_type, activity_items, created_at")
        .eq("conversation_id", thread_id)
        .order("created_at")
        .execute()
    )

    return {
        "thread": conv.data,
        "messages": msgs.data,
        "is_owner": is_owner,
    }


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    supabase = get_supabase()

    # Verify ownership
    conv = (
        supabase.table("marketing_conversations")
        .select("owner_clerk_id")
        .eq("id", thread_id)
        .single()
        .execute()
    )
    if not conv.data or conv.data["owner_clerk_id"] != context.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete messages first, then conversation
    supabase.table("marketing_messages").delete().eq(
        "conversation_id", thread_id
    ).execute()
    supabase.table("marketing_conversations").delete().eq(
        "id", thread_id
    ).execute()

    return {"status": "ok"}


@router.put("/threads/{thread_id}/title")
async def rename_thread(
    thread_id: str,
    body: RenameRequest,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    supabase = get_supabase()

    conv = (
        supabase.table("marketing_conversations")
        .select("owner_clerk_id")
        .eq("id", thread_id)
        .single()
        .execute()
    )
    if not conv.data or conv.data["owner_clerk_id"] != context.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    supabase.table("marketing_conversations").update(
        {"title": body.title[:100]}
    ).eq("id", thread_id).execute()

    return {"status": "ok"}
