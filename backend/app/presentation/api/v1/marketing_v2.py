"""
Marketing AI V2 - Native SSE + ADK Implementation

This module provides the V2 version of the marketing AI endpoints using:
- Google Agent Development Kit (ADK)
- Gemini 3 Flash
- Native SSE streaming (no ChatKit dependency)

The original marketing.py (/marketing) uses ChatKit and is preserved for backward compatibility.
This V2 module (/marketing-v2) provides the new ADK-based implementation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Annotated
import uuid

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from starlette.responses import StreamingResponse
from pydantic import BaseModel

# Shared dependencies from the original marketing module
from app.infrastructure.chatkit.context import MarketingRequestContext
from app.infrastructure.chatkit.model_assets import get_model_asset
from app.infrastructure.chatkit.supabase_store import generate_thread_title
from app.infrastructure.config.settings import get_settings
from app.infrastructure.supabase.client import get_supabase
from app.infrastructure.security.marketing_token_service import (
    MarketingTokenError,
    MarketingTokenService,
)

# V2-specific: Agent service (supports both ADK and OpenAI backends)
from app.infrastructure.marketing.agent_service import get_marketing_agent_service

router = APIRouter(prefix="/marketing-v2", tags=["marketing-v2"])
logger = logging.getLogger(__name__)


# ============================================================
# Auth: Reuse token service from shared infrastructure
# ============================================================

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
    """Validate marketing client token and return request context."""
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return MarketingRequestContext(
        user_id=claims.sub,
        user_email=claims.email,
        user_name=claims.name,
        model_asset_id=model_asset_id,
    )


# ============================================================
# Request/Response Models
# ============================================================

class FileAttachment(BaseModel):
    """File attachment for multimodal chat."""
    filename: str
    mime_type: str
    data: str  # base64-encoded file content
    size_bytes: int


# Allowed MIME types for file uploads
_ALLOWED_MIME_PREFIXES = ("image/", "application/pdf", "text/csv", "text/plain", "text/markdown")
_ALLOWED_MIME_EXACT = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
}
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
_MAX_TOTAL_SIZE = 20 * 1024 * 1024  # 20MB total
_MAX_FILE_COUNT = 5


class ChatStreamRequest(BaseModel):
    """Request body for the native SSE chat endpoint."""
    message: str
    conversation_id: str | None = None
    context_items: list[dict] | None = None
    model_asset_id: str | None = None
    attachments: list[FileAttachment] | None = None


# ============================================================
# Native SSE Streaming Endpoint (ADK)
# ============================================================

@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    body: ChatStreamRequest,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """
    Native SSE streaming endpoint for marketing AI chat (V2 - ADK).

    Uses Google ADK with Gemini 3 Flash for multi-agent orchestration.
    Returns SSE events in the format:
    - text_delta: Incremental text content
    - tool_call: Tool invocation start
    - tool_result: Tool execution result
    - reasoning: Agent reasoning/thinking
    - sub_agent_event: Sub-agent activity (detailed)
    - chart: Chart specification for visualization
    - progress: Keepalive progress indicator
    - done: Stream completion
    - error: Error event
    """
    agent_service = get_marketing_agent_service()
    sb = get_supabase()

    # Validate attachments
    attachments_data: list[dict] | None = None
    if body.attachments:
        if len(body.attachments) > _MAX_FILE_COUNT:
            raise HTTPException(
                status_code=400,
                detail=f"ファイルは最大{_MAX_FILE_COUNT}個まで添付できます",
            )

        total_size = 0
        attachments_data = []
        for att in body.attachments:
            # Validate MIME type
            mime_ok = any(att.mime_type.startswith(p) for p in _ALLOWED_MIME_PREFIXES) or att.mime_type in _ALLOWED_MIME_EXACT
            if not mime_ok:
                raise HTTPException(
                    status_code=400,
                    detail=f"非対応のファイル形式です: {att.mime_type}",
                )

            # Validate file size
            if att.size_bytes > _MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"ファイルサイズが上限(10MB)を超えています: {att.filename}",
                )
            total_size += att.size_bytes

            attachments_data.append({
                "filename": att.filename,
                "mime_type": att.mime_type,
                "data": att.data,
                "size_bytes": att.size_bytes,
            })

        if total_size > _MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400,
                detail="添付ファイルの合計サイズが上限(20MB)を超えています",
            )

    # Load model asset if specified
    model_asset = None
    asset_id = body.model_asset_id or context.model_asset_id
    if asset_id:
        model_asset = get_model_asset(asset_id, context=context)

    # Determine or create conversation ID
    conversation_id = body.conversation_id or str(uuid.uuid4())
    is_new_conversation = not body.conversation_id

    async def event_generator():
        # --- Immediate feedback: Client receives this before any heavy work ---
        yield f"data: {json.dumps({'type': 'progress', 'text': 'リクエストを処理中...'}, ensure_ascii=False)}\n\n"

        # --- DB: Save user message before streaming ---
        user_msg_id = str(uuid.uuid4())
        try:
            # Ensure conversation exists
            if is_new_conversation:
                # Generate title asynchronously
                title = await generate_thread_title(body.message) or "新しい会話"
                sb.table("marketing_conversations").insert({
                    "id": conversation_id,
                    "title": title,
                    "owner_email": context.user_email,
                    "owner_clerk_id": context.user_id,
                    "status": "active",
                    "metadata": {
                        "engine": "adk",  # Mark as V2/ADK conversation
                        "context_items": body.context_items,
                    } if body.context_items else {"engine": "adk"},
                }).execute()
                logger.info(f"[DB] Created V2 conversation: {conversation_id}")
            else:
                # Update last_message_at for existing conversation
                sb.table("marketing_conversations").update({
                    "last_message_at": datetime.utcnow().isoformat(),
                }).eq("id", conversation_id).execute()

            # Save user message
            sb.table("marketing_messages").insert({
                "id": user_msg_id,
                "conversation_id": conversation_id,
                "role": "user",
                "message_type": "content",
                "content": {"text": body.message},
                "plain_text": body.message,
                "created_by": context.user_email,
            }).execute()
            logger.info(f"[DB] Saved user message: {user_msg_id}")
        except Exception as e:
            logger.exception(f"[DB] Failed to save user message: {e}")
            # Continue streaming even if DB save fails

        # --- Streaming with activity items accumulation ---
        activity_items: list[dict] = []
        full_text_content = ""
        seq = 0
        current_text_id: str | None = None

        try:
            async for event in agent_service.stream_chat(
                user_id=context.user_id,
                user_email=context.user_email,
                conversation_id=conversation_id,
                message=body.message,
                context_items=body.context_items,
                model_asset=model_asset,
                attachments=attachments_data,
            ):
                if await request.is_disconnected():
                    logger.info("Client disconnected during chat stream")
                    break

                event_type = event.get("type")

                # --- Accumulate activity items for DB storage ---
                if event_type == "text_delta":
                    content = event.get("content", "")
                    full_text_content += content
                    if current_text_id is None:
                        current_text_id = str(uuid.uuid4())
                        activity_items.append({
                            "kind": "text",
                            "sequence": seq,
                            "id": current_text_id,
                            "content": content,
                        })
                        seq += 1
                    else:
                        # Update existing text item
                        for item in activity_items:
                            if item.get("id") == current_text_id:
                                item["content"] = item.get("content", "") + content
                                break

                elif event_type == "response_created":
                    current_text_id = None  # Reset for new response

                elif event_type == "tool_call":
                    # Reset text ID so subsequent text starts a new block
                    current_text_id = None
                    activity_items.append({
                        "kind": "tool",
                        "sequence": seq,
                        "id": event.get("call_id"),
                        "name": event.get("name"),
                        "call_id": event.get("call_id"),
                        "arguments": event.get("arguments"),
                    })
                    seq += 1

                elif event_type == "tool_result":
                    # Update matching tool item with output
                    call_id = event.get("call_id")
                    for item in reversed(activity_items):
                        if (
                            item.get("kind") == "tool"
                            and item.get("call_id") == call_id
                            and "output" not in item
                        ):
                            item["output"] = event.get("output", "(completed)")
                            break

                elif event_type == "reasoning":
                    activity_items.append({
                        "kind": "reasoning",
                        "sequence": seq,
                        "id": str(uuid.uuid4()),
                        "content": event.get("content"),
                    })
                    seq += 1

                elif event_type == "sub_agent_event":
                    # Reset text ID so subsequent text starts a new block
                    current_text_id = None
                    activity_items.append({
                        "kind": "sub_agent",
                        "sequence": seq,
                        "id": str(uuid.uuid4()),
                        "agent": event.get("agent"),
                        "event_type": event.get("event_type"),
                        "is_running": event.get("is_running"),
                        "data": event.get("data"),
                    })
                    seq += 1

                elif event_type == "code_execution":
                    # Code execution from CodeExecutionAgent
                    current_text_id = None
                    activity_items.append({
                        "kind": "code_execution",
                        "sequence": seq,
                        "id": str(uuid.uuid4()),
                        "code": event.get("code", ""),
                        "language": event.get("language", "PYTHON"),
                    })
                    seq += 1

                elif event_type == "code_result":
                    # Code execution result
                    activity_items.append({
                        "kind": "code_result",
                        "sequence": seq,
                        "id": str(uuid.uuid4()),
                        "output": event.get("output", ""),
                        "outcome": event.get("outcome", "UNKNOWN"),
                    })
                    seq += 1

                elif event_type == "chart":
                    # Reset text ID so subsequent text starts a new block
                    current_text_id = None
                    activity_items.append({
                        "kind": "chart",
                        "sequence": seq,
                        "id": str(uuid.uuid4()),
                        "spec": event.get("spec"),
                    })
                    seq += 1

                elif event_type == "_context_items":
                    # Save context_items to conversation metadata
                    try:
                        sb.table("marketing_conversations").update({
                            "metadata": {
                                "engine": "adk",
                                "context_items": event.get("items"),
                            },
                        }).eq("id", conversation_id).execute()
                        logger.info(f"[DB] Saved context_items for: {conversation_id}")
                    except Exception as e:
                        logger.warning(f"[DB] Failed to save context_items: {e}")
                    # Send to client for next turn context
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    continue

                # Translate reasoning if flagged
                if event.get("_needs_translation"):
                    try:
                        if event.get("content"):
                            translated = await agent_service._translate_to_japanese(
                                event["content"]
                            )
                            event["content"] = translated
                        elif event.get("data", {}).get("content"):
                            translated = await agent_service._translate_to_japanese(
                                event["data"]["content"]
                            )
                            event["data"]["content"] = translated
                    except Exception as te:
                        logger.warning(f"Translation failed: {te}")

                # Remove internal flags before sending
                event.pop("_needs_translation", None)

                # Override conversation_id in done event
                if event_type == "done":
                    event["conversation_id"] = conversation_id

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # --- Safety net: Mark any unfinished items as completed ---
            for item in activity_items:
                if item.get("kind") == "tool" and "output" not in item:
                    item["output"] = "(completed)"
                elif item.get("kind") == "sub_agent" and item.get("is_running"):
                    item["is_running"] = False

            # --- DB: Save assistant message with activity_items ---
            if full_text_content or activity_items:
                assistant_msg_id = str(uuid.uuid4())
                try:
                    sb.table("marketing_messages").insert({
                        "id": assistant_msg_id,
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "message_type": "content",
                        "content": {
                            "text": full_text_content,
                            "activity_items": activity_items,
                        },
                        "plain_text": full_text_content[:10000] if full_text_content else None,
                        "created_by": "assistant",
                    }).execute()
                    logger.info(f"[DB] Saved assistant message: {assistant_msg_id}")

                    # Update conversation last_message_at
                    sb.table("marketing_conversations").update({
                        "last_message_at": datetime.utcnow().isoformat(),
                    }).eq("id", conversation_id).execute()
                except Exception as e:
                    logger.exception(f"[DB] Failed to save assistant message: {e}")

        except Exception as e:
            logger.exception("Error in V2 chat stream")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# Thread Management Endpoints (V2)
# ============================================================

@router.get("/threads")
async def list_threads(
    context: MarketingRequestContext = Depends(require_marketing_context),
    limit: int = 50,
):
    """
    List user's V2 conversations for history panel.

    Returns conversations sorted by last_message_at (newest first).
    Filters to ADK-engine conversations only.
    """
    sb = get_supabase()

    try:
        # Get user's own conversations (V2 only)
        result = (
            sb.table("marketing_conversations")
            .select("id, title, status, created_at, last_message_at, updated_at, metadata")
            .eq("owner_email", context.user_email)
            .order("last_message_at", desc=True)
            .limit(limit)
            .execute()
        )

        conversations = []
        for row in result.data or []:
            # Filter to ADK-engine conversations
            metadata = row.get("metadata") or {}
            if metadata.get("engine") != "adk":
                continue

            conversations.append({
                "id": row["id"],
                "title": row.get("title") or "新しい会話",
                "status": row.get("status"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("last_message_at") or row.get("updated_at") or row.get("created_at"),
            })

        return {"conversations": conversations}
    except Exception as exc:
        logger.exception("Failed to list V2 threads")
        raise HTTPException(status_code=500, detail="Failed to list conversations") from exc


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """
    Delete a V2 conversation and its messages.
    """
    sb = get_supabase()

    try:
        # Verify ownership
        conv_result = (
            sb.table("marketing_conversations")
            .select("owner_email")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conv_result.data[0].get("owner_email") != context.user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete messages first (foreign key constraint)
        sb.table("marketing_messages").delete().eq("conversation_id", thread_id).execute()

        # Delete conversation
        sb.table("marketing_conversations").delete().eq("id", thread_id).execute()

        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to delete conversation") from exc


@router.get("/threads/{thread_id}")
async def get_thread_detail(
    thread_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """
    Get V2 conversation detail with messages.

    Returns conversation metadata and messages with activity_items for UI restoration.
    """
    sb = get_supabase()

    try:
        # Get conversation
        conv_result = (
            sb.table("marketing_conversations")
            .select("*")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation = conv_result.data[0]

        # Check access (owner or shared)
        is_owner = conversation.get("owner_email") == context.user_email
        is_shared = conversation.get("metadata", {}).get("is_shared", False)
        if not is_owner and not is_shared:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get messages
        messages_result = (
            sb.table("marketing_messages")
            .select("id, role, message_type, content, plain_text, created_at")
            .eq("conversation_id", thread_id)
            .order("created_at", desc=False)
            .limit(500)
            .execute()
        )

        messages = []
        for row in messages_result.data or []:
            content = row.get("content") or {}
            msg = {
                "id": row["id"],
                "role": row["role"],
                "content": content.get("text") or row.get("plain_text") or "",
                "activity_items": content.get("activity_items"),
                "created_at": row.get("created_at"),
            }
            messages.append(msg)

        # Get context_items from conversation metadata
        context_items = conversation.get("metadata", {}).get("context_items")

        return {
            "conversation": {
                "id": conversation["id"],
                "title": conversation.get("title"),
                "status": conversation.get("status"),
                "created_at": conversation.get("created_at"),
                "last_message_at": conversation.get("last_message_at"),
                "is_owner": is_owner,
            },
            "messages": messages,
            "context_items": context_items,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to load conversation") from exc
